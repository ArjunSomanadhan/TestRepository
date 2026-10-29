"""LLM and embedding providers: Azure OpenAI → OpenAI → mock fallback."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from knowledge_ops.config import Settings, get_settings


class MockEmbeddings:
    """Deterministic bag-of-words style embeddings for offline demos/tests."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vec
        for tok in tokens:
            digest = hashlib.sha256(tok.encode()).digest()
            idx = digest[0] % self.dim
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            weight = 1.0 + (digest[2] / 255.0)
            vec[idx] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)


class MockChatModel:
    """Lightweight rule/context LLM so the graph runs without API keys."""

    def invoke(self, prompt: str) -> str:
        lower = prompt.lower()
        if "decompose" in lower or "sub-queries" in lower or "plan the following" in lower:
            return self._plan(prompt)
        if "verify" in lower or "grounding" in lower:
            return self._verify(prompt)
        return self._answer(prompt)

    def _extract_query(self, prompt: str) -> str:
        for marker in ("User question:", "Question:", "Query:"):
            if marker in prompt:
                return prompt.split(marker, 1)[1].strip().split("\n", 1)[0].strip()
        return prompt.strip().split("\n", 1)[0][:240]

    def _plan(self, prompt: str) -> str:
        q = self._extract_query(prompt)
        tokens = [t for t in re.findall(r"[A-Za-z0-9\-]+", q) if len(t) > 3][:8]
        focus = " ".join(tokens[:5]) or q[:80]
        return (
            "PLAN:\n"
            f"1. Retrieve policy/SOP details related to: {focus}\n"
            f"2. Retrieve related constraints, SLAs, or exceptions for: {focus}\n"
            "3. Synthesize a grounded answer with citations\n"
            "SUB_QUERIES:\n"
            f"- {focus}\n"
            f"- {focus} exceptions approval SLA\n"
            f"- {focus} security requirements"
        )

    def _evidence_blocks(self, prompt: str) -> list[tuple[str, str]]:
        # Only parse material after an Evidence: marker so instruction
        # examples like [source:filename#id] are not treated as docs.
        section = prompt
        for marker in ("Evidence:", "EVIDENCE:"):
            if marker in prompt:
                section = prompt.split(marker, 1)[1]
                break
        blocks: list[tuple[str, str]] = []
        for m in re.finditer(
            r"\[source:([^\]]+)\]\s*(.*?)(?=\[source:|\Z)", section, flags=re.S
        ):
            src = m.group(1).strip()
            text = m.group(2).strip()
            if src.lower() in {"filename#id", "file#id"}:
                continue
            if text:
                blocks.append((src, text))
        return blocks

    def _best_sentences(self, text: str, q_tokens: set[str], limit: int = 2) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        ranked: list[tuple[float, str]] = []
        for sent in sentences:
            clean = " ".join(sent.split())
            if len(clean) < 25:
                continue
            toks = set(re.findall(r"[a-z0-9]+", clean.lower()))
            overlap = len(q_tokens & toks) / max(1, len(q_tokens))
            if overlap > 0:
                ranked.append((overlap, clean))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in ranked[:limit]]

    def _answer(self, prompt: str) -> str:
        evidence = self._evidence_blocks(prompt)
        q = self._extract_query(prompt)
        if not evidence:
            return (
                "I do not have enough retrieved enterprise documentation to answer "
                f"confidently about: {q}. Please ingest relevant policies/SOPs."
            )
        q_tokens = set(re.findall(r"[a-z0-9]+", q.lower()))
        scored: list[tuple[float, str, str]] = []
        for src, text in evidence:
            t_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
            overlap = len(q_tokens & t_tokens) / max(1, len(q_tokens))
            scored.append((overlap, src, text))
        scored.sort(key=lambda x: x[0], reverse=True)
        bullets: list[str] = []
        used_srcs: set[str] = set()
        for overlap, src, text in scored:
            if src in used_srcs or overlap < 0.12:
                continue
            for sent in self._best_sentences(text, q_tokens):
                bullets.append(f"- {sent[:320]} [source:{src}]")
                used_srcs.add(src)
                break
            if len(bullets) >= 3:
                break
        if not bullets:
            for _, src, text in scored[:2]:
                snippet = " ".join(text.split())[:280]
                bullets.append(f"- {snippet} [source:{src}]")
        body = "\n".join(bullets)
        return (
            f"Based on the retrieved enterprise documents for “{q}”:\n\n"
            f"{body}\n\n"
            "Summary: The answer above is synthesized only from the cited sources. "
            "Follow the referenced policy/SOP for authoritative steps and SLAs."
        )

    def _verify(self, prompt: str) -> str:
        # Prefer lexical verifier in guardrails; this is a soft LLM-shaped hint.
        return "GROUNDED: partial\nCONFIDENCE: 0.6\nFLAGS: none"


_CHAT: Any | None = None
_EMBED: Any | None = None
_PROVIDER: str | None = None


def resolve_provider(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.llm_provider in {"azure", "openai", "mock"}:
        if settings.llm_provider == "azure" and not (
            settings.azure_api_key and settings.azure_endpoint
        ):
            return "mock"
        if settings.llm_provider == "openai" and not settings.openai_api_key:
            return "mock"
        return settings.llm_provider
    # auto
    if settings.azure_api_key and settings.azure_endpoint:
        return "azure"
    if settings.openai_api_key:
        return "openai"
    return "mock"


def get_chat_model(settings: Settings | None = None):
    global _CHAT, _PROVIDER
    settings = settings or get_settings()
    provider = resolve_provider(settings)
    if _CHAT is not None and _PROVIDER == provider:
        return _CHAT
    _PROVIDER = provider
    if provider == "azure":
        from langchain_openai import AzureChatOpenAI

        _CHAT = AzureChatOpenAI(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            azure_deployment=settings.azure_deployment,
            temperature=0,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        _CHAT = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            temperature=0,
        )
    else:
        _CHAT = MockChatModel()
    return _CHAT


def get_embeddings(settings: Settings | None = None):
    global _EMBED, _PROVIDER
    settings = settings or get_settings()
    provider = resolve_provider(settings)
    # embeddings cache keyed loosely with chat provider
    if _EMBED is not None and _PROVIDER == provider:
        return _EMBED
    if provider == "azure":
        from langchain_openai import AzureOpenAIEmbeddings

        _EMBED = AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_endpoint,
            api_key=settings.azure_api_key,
            api_version=settings.azure_api_version,
            azure_deployment=settings.azure_embedding_deployment,
        )
    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        _EMBED = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
        )
    else:
        _EMBED = MockEmbeddings()
    return _EMBED


def chat(prompt: str, settings: Settings | None = None) -> str:
    model = get_chat_model(settings)
    result = model.invoke(prompt)
    if hasattr(result, "content"):
        return str(result.content)
    return str(result)


def reset_llm_cache() -> None:
    global _CHAT, _EMBED, _PROVIDER
    _CHAT = None
    _EMBED = None
    _PROVIDER = None
