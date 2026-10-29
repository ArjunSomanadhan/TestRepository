"""Input validation and output grounding helpers."""

from __future__ import annotations

import re
from typing import Iterable

from knowledge_ops.state import RetrievedDoc, ValidationResult

MAX_QUERY_CHARS = 2000

_BLOCKED_PATTERNS = [
    re.compile(r"(?i)\bignore (all|previous) instructions\b"),
    re.compile(r"(?i)\bjailbreak\b"),
    re.compile(r"(?i)\bexfiltrat(e|ion)\b.*\bcredentials?\b"),
]


def validate_input(query: str) -> tuple[bool, str]:
    text = (query or "").strip()
    if not text:
        return False, "Query is empty."
    if len(text) > MAX_QUERY_CHARS:
        return False, f"Query exceeds {MAX_QUERY_CHARS} characters."
    for pat in _BLOCKED_PATTERNS:
        if pat.search(text):
            return False, "Query blocked by input guardrail."
    return True, ""


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def claim_supported(claim: str, docs: Iterable[RetrievedDoc], min_overlap: float = 0.28) -> bool:
    claim_toks = _tokenize(claim)
    if not claim_toks:
        return True
    for doc in docs:
        doc_toks = _tokenize(doc.get("text", ""))
        if not doc_toks:
            continue
        overlap = len(claim_toks & doc_toks) / len(claim_toks)
        if overlap >= min_overlap:
            return True
        # Also accept if the claim mostly cites a known source tag and shares some tokens
        if "[source:" in claim.lower() and overlap >= min_overlap * 0.6:
            return True
    return False


def verify_grounding(
    answer: str,
    docs: list[RetrievedDoc],
    confidence_threshold: float = 0.55,
) -> ValidationResult:
    flags: list[str] = []
    unsupported: list[str] = []

    if not docs:
        return ValidationResult(
            grounded=False,
            confidence=0.0,
            flags=["insufficient_context"],
            unsupported_claims=[],
            grounding_score=0.0,
        )

    corpus = " ".join(d.get("text", "") for d in docs)
    corpus_toks = _tokenize(corpus)
    answer_toks = _tokenize(answer)
    lexical = (
        len(answer_toks & corpus_toks) / max(1, len(answer_toks)) if answer_toks else 0.0
    )

    cited = len(re.findall(r"\[source:[^\]]+\]", answer))
    citation_bonus = min(0.25, 0.08 * cited)

    claims = _sentences(answer)
    # Skip purely meta sentences
    substantive = [
        c
        for c in claims
        if not c.lower().startswith("summary:")
        and "synthesized only from" not in c.lower()
    ]
    if not substantive:
        substantive = claims or [answer]

    for claim in substantive:
        if not claim_supported(claim, docs):
            unsupported.append(claim)

    support_ratio = 1.0 - (len(unsupported) / max(1, len(substantive)))
    grounding_score = max(0.0, min(1.0, 0.55 * support_ratio + 0.30 * lexical + citation_bonus))
    confidence = grounding_score

    if unsupported:
        flags.append("ungrounded_claim")
    if not cited:
        flags.append("missing_citations")
    if confidence < confidence_threshold:
        flags.append("low_confidence")
    if len(docs) < 2:
        flags.append("narrow_retrieval")

    grounded = support_ratio >= 0.6 and cited > 0 and confidence >= confidence_threshold * 0.85

    return ValidationResult(
        grounded=grounded,
        confidence=round(confidence, 3),
        flags=flags,
        unsupported_claims=unsupported[:5],
        grounding_score=round(grounding_score, 3),
    )


def disclaimers_for(validation: ValidationResult) -> list[str]:
    notes: list[str] = [
        "Answers are generated from retrieved enterprise documents and may be incomplete."
    ]
    flags = validation.get("flags") or []
    if "low_confidence" in flags or not validation.get("grounded", False):
        notes.append(
            "Low confidence or incomplete grounding detected — verify against the cited source documents before acting."
        )
    if "insufficient_context" in flags:
        notes.append("Insufficient retrieved context; treat this as informational only.")
    if "ungrounded_claim" in flags:
        notes.append("Some statements could not be fully matched to retrieved sources.")
    return notes
