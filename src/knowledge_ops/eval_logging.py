"""Structured evaluation logs and decision traces."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_ops.config import Settings, get_settings
from knowledge_ops.state import KnowledgeOpsState, TraceEvent


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def trace(agent: str, event: str, detail: str = "") -> TraceEvent:
    return TraceEvent(agent=agent, event=event, detail=detail, ts=now_iso())


def ensure_log_dirs(settings: Settings | None = None) -> tuple[Path, Path]:
    settings = settings or get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    traces = settings.logs_dir / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    return settings.logs_dir, traces


def write_trace_file(state: KnowledgeOpsState, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    _, traces_dir = ensure_log_dirs(settings)
    run_id = state.get("run_id") or new_run_id()
    path = traces_dir / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "session_id": state.get("session_id"),
        "query": state.get("query"),
        "plan": state.get("plan"),
        "sub_queries": state.get("sub_queries"),
        "retrieved_docs": [
            {
                "id": d.get("id"),
                "source": d.get("source"),
                "score": d.get("score"),
                "text": (d.get("text") or "")[:500],
            }
            for d in state.get("retrieved_docs") or []
        ],
        "draft_answer": state.get("draft_answer"),
        "verified_answer": state.get("verified_answer"),
        "validation": state.get("validation"),
        "traces": state.get("traces"),
        "disclaimers": state.get("disclaimers"),
        "refused": state.get("refused", False),
        "refusal_reason": state.get("refusal_reason"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def append_eval_log(
    state: KnowledgeOpsState,
    *,
    latency_ms: float,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    logs_dir, _ = ensure_log_dirs(settings)
    path = logs_dir / "eval.jsonl"
    validation = state.get("validation") or {}
    retrieved = state.get("retrieved_docs") or []
    flags = validation.get("flags") or []
    record = {
        "ts": now_iso(),
        "run_id": state.get("run_id"),
        "session_id": state.get("session_id"),
        "query": state.get("query"),
        "latency_ms": round(latency_ms, 2),
        "retrieval_count": len(retrieved),
        "unique_sources": sorted({d.get("source", "") for d in retrieved if d.get("source")}),
        "grounding_score": validation.get("grounding_score"),
        "confidence": validation.get("confidence"),
        "grounded": validation.get("grounded"),
        "flags": flags,
        "pass": bool(validation.get("grounded")) and "low_confidence" not in flags,
        "refused": bool(state.get("refused")),
        "verify_attempts": state.get("verify_attempts", 0),
        "sub_query_count": len(state.get("sub_queries") or []),
        "provider_hint": "see llm.resolve_provider",
    }
    # merge any extra eval_log from state
    extra = state.get("eval_log") or {}
    record.update({k: v for k, v in extra.items() if k not in record})
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return path


class Timer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self.start) * 1000.0


def build_final_response(
    state: KnowledgeOpsState, *, trace_path: str | None = None
) -> dict[str, Any]:
    validation = state.get("validation") or {}
    docs = state.get("retrieved_docs") or []
    answer = state.get("verified_answer") or state.get("draft_answer") or ""
    if state.get("refused"):
        answer = state.get("refusal_reason") or "Request refused by guardrails."
    sources = []
    seen = set()
    for d in docs:
        key = (d.get("source"), d.get("id"))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "id": d.get("id"),
                "source": d.get("source"),
                "score": d.get("score"),
                "excerpt": (d.get("text") or "")[:240],
            }
        )
    return {
        "run_id": state.get("run_id"),
        "answer": answer,
        "sources": sources,
        "validation": validation,
        "disclaimers": state.get("disclaimers") or [],
        "plan": state.get("plan"),
        "traces": state.get("traces") or [],
        "trace_path": trace_path,
        "refused": bool(state.get("refused")),
    }
