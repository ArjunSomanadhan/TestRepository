"""Verifier agent: grounding, confidence, flags."""

from __future__ import annotations

from typing import Any

from knowledge_ops.config import get_settings
from knowledge_ops.eval_logging import trace
from knowledge_ops.guardrails import disclaimers_for, verify_grounding
from knowledge_ops.state import KnowledgeOpsState


def verify_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    if state.get("refused"):
        return {"traces": [trace("verifier", "skipped", "request refused")]}

    answer = state.get("draft_answer") or ""
    docs = state.get("retrieved_docs") or []
    validation = verify_grounding(
        answer, docs, confidence_threshold=settings.confidence_threshold
    )
    attempts = int(state.get("verify_attempts") or 0) + 1
    disclaimers = disclaimers_for(validation)

    # Cap answer when still weak after retries
    verified = answer
    if not validation.get("grounded") and attempts > settings.max_verify_retries:
        verified = (
            answer
            + "\n\n[Limited answer] Validation did not fully confirm grounding. "
            "Please consult the cited sources before making operational decisions."
        )
        flags = list(validation.get("flags") or [])
        if "low_confidence" not in flags:
            flags.append("low_confidence")
        validation = {**validation, "flags": flags}

    return {
        "validation": validation,
        "verified_answer": verified,
        "disclaimers": disclaimers,
        "verify_attempts": attempts,
        "traces": [
            trace(
                "verifier",
                "validated",
                f"grounded={validation.get('grounded')}; "
                f"confidence={validation.get('confidence')}; "
                f"flags={validation.get('flags')}; attempt={attempts}",
            )
        ],
    }


def should_retry_analysis(state: KnowledgeOpsState) -> str:
    settings = get_settings()
    if state.get("refused"):
        return "finalize"
    validation = state.get("validation") or {}
    attempts = int(state.get("verify_attempts") or 0)
    needs_retry = (not validation.get("grounded")) or (
        "low_confidence" in (validation.get("flags") or [])
    )
    if needs_retry and attempts <= settings.max_verify_retries:
        return "analyze"
    return "finalize"
