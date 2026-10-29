"""Analyst agent: synthesize grounded draft answers."""

from __future__ import annotations

from typing import Any

from knowledge_ops.config import get_settings
from knowledge_ops.eval_logging import trace
from knowledge_ops.llm import chat
from knowledge_ops.state import KnowledgeOpsState


def _format_evidence(state: KnowledgeOpsState) -> str:
    docs = state.get("retrieved_docs") or []
    parts = []
    for d in docs:
        src = d.get("source", "unknown")
        chunk_id = d.get("id", "")
        label = f"{src}#{chunk_id}"
        parts.append(f"[source:{label}]\n{d.get('text', '')}\n")
    return "\n".join(parts)


def analyze_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    if state.get("refused"):
        return {"traces": [trace("analyst", "skipped", "request refused")]}

    evidence = _format_evidence(state)
    memory = state.get("memory_context") or ""
    plan = state.get("plan") or {}
    revision_note = ""
    validation = state.get("validation") or {}
    if validation.get("flags"):
        revision_note = (
            "Previous draft had validation issues: "
            f"{validation.get('flags')}. Unsupported: "
            f"{validation.get('unsupported_claims')}. "
            "Revise to only use evidence and cite sources as [source:file#id]."
        )

    prompt = (
        "You are the Analyst for an enterprise knowledge operations agent.\n"
        "Answer the user question using ONLY the evidence below. "
        "Cite each used chunk with the exact [source:...] tag from the evidence. "
        "If evidence is insufficient, say what is missing.\n\n"
        f"User question: {state.get('query')}\n"
        f"Plan steps: {plan.get('steps')}\n"
        f"Memory context: {memory}\n"
        f"{revision_note}\n\n"
        f"Evidence:\n{evidence}\n"
    )
    draft = chat(prompt, settings)
    return {
        "draft_answer": draft,
        "traces": [trace("analyst", "drafted", draft[:240])],
    }
