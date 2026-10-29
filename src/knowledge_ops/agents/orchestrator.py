"""Orchestrator: input gate, planning, finalization."""

from __future__ import annotations

import re
from typing import Any

from knowledge_ops.config import get_settings
from knowledge_ops.eval_logging import (
    append_eval_log,
    build_final_response,
    new_run_id,
    trace,
    write_trace_file,
    Timer,
)
from knowledge_ops.guardrails import disclaimers_for, validate_input
from knowledge_ops.llm import chat
from knowledge_ops.state import KnowledgeOpsState, ValidationResult


def _parse_plan(raw: str, query: str) -> tuple[dict[str, Any], list[str]]:
    sub_queries: list[str] = []
    in_subs = False
    steps: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("SUB_QUERIES"):
            in_subs = True
            continue
        if stripped.upper().startswith("PLAN"):
            in_subs = False
            continue
        if in_subs:
            q = re.sub(r"^[-*\d.)\s]+", "", stripped).strip()
            if q:
                sub_queries.append(q)
        elif re.match(r"^\d+[.)]", stripped) or stripped.startswith("-"):
            steps.append(re.sub(r"^[-*\d.)\s]+", "", stripped).strip())
    if not sub_queries:
        sub_queries = [query, f"{query} policy exceptions SLA", f"{query} requirements"]
    if not steps:
        steps = [
            "Retrieve relevant enterprise documents",
            "Synthesize grounded answer",
            "Verify citations and confidence",
        ]
    plan = {"rationale": "Decompose the question for multi-document retrieval.", "steps": steps}
    return plan, sub_queries[:5]


def orchestrate_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    query = (state.get("query") or "").strip()
    run_id = state.get("run_id") or new_run_id()
    ok, reason = validate_input(query)
    events = [trace("orchestrator", "received_query", query[:200])]
    if not ok:
        events.append(trace("orchestrator", "guardrail_block", reason))
        validation = ValidationResult(
            grounded=False,
            confidence=0.0,
            flags=["guardrail_triggered"],
            unsupported_claims=[],
            grounding_score=0.0,
        )
        return {
            "run_id": run_id,
            "refused": True,
            "refusal_reason": reason,
            "validation": validation,
            "disclaimers": disclaimers_for(validation),
            "traces": events,
            "sub_queries": [],
            "plan": {"steps": [], "rationale": "Blocked by input guardrail."},
            "verify_attempts": 0,
        }

    prompt = (
        "You are the Orchestrator for an enterprise knowledge ops agent.\n"
        "Plan the following user question by listing numbered steps and 2-4 SUB_QUERIES "
        "for retrieval across policies and SOPs.\n\n"
        f"User question: {query}\n"
    )
    raw = chat(prompt, settings)
    plan, sub_queries = _parse_plan(raw, query)
    events.append(
        trace(
            "orchestrator",
            "plan_created",
            f"steps={len(plan['steps'])}; sub_queries={sub_queries}",
        )
    )
    return {
        "run_id": run_id,
        "refused": False,
        "plan": plan,
        "sub_queries": sub_queries,
        "traces": events,
        "verify_attempts": 0,
        "eval_log": {"_timer_start": True},
    }


def finalize_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    events = [trace("orchestrator", "finalize", "Assembling response envelope")]
    validation = state.get("validation") or ValidationResult(
        grounded=False, confidence=0.0, flags=["insufficient_context"], unsupported_claims=[], grounding_score=0.0
    )
    disclaimers = state.get("disclaimers") or disclaimers_for(validation)
    # Prefer verified answer; fall back to draft
    answer = state.get("verified_answer") or state.get("draft_answer") or ""
    if state.get("refused"):
        answer = state.get("refusal_reason") or answer

    # Persist traces + eval (latency approximated if timer absent)
    timer = Timer()
    latency = float((state.get("eval_log") or {}).get("latency_ms") or timer.ms())
    merged: KnowledgeOpsState = {
        **state,
        "verified_answer": answer,
        "disclaimers": disclaimers,
        "traces": (state.get("traces") or []) + events,
    }
    trace_path = write_trace_file(merged, settings)
    eval_path = append_eval_log(merged, latency_ms=latency, settings=settings)
    final = build_final_response(merged, trace_path=str(trace_path))
    events.append(
        trace("orchestrator", "logged", f"trace={trace_path.name}; eval={eval_path.name}")
    )
    return {
        "verified_answer": answer,
        "disclaimers": disclaimers,
        "final_response": final,
        "traces": events,
        "eval_log": {"latency_ms": latency, "eval_path": str(eval_path), "trace_path": str(trace_path)},
    }
