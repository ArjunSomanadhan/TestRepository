"""Memory agent: short-term session memory for follow-up context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from knowledge_ops.config import get_settings
from knowledge_ops.eval_logging import trace
from knowledge_ops.state import KnowledgeOpsState


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sessions": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sessions": {}}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def memory_load_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    session_id = state.get("session_id") or "default"
    data = _load(settings.memory_path)
    turns = data.get("sessions", {}).get(session_id, [])
    if not turns:
        context = ""
    else:
        recent = turns[-3:]
        lines = []
        for t in recent:
            lines.append(f"Q: {t.get('query')}\nA: {t.get('answer', '')[:300]}")
        context = "\n---\n".join(lines)
    return {
        "memory_context": context,
        "traces": [
            trace(
                "memory",
                "loaded",
                f"session={session_id}; turns={len(turns)}; context_chars={len(context)}",
            )
        ],
    }


def memory_store_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    session_id = state.get("session_id") or "default"
    if state.get("refused"):
        return {"traces": [trace("memory", "skipped_store", "refused request")]}

    data = _load(settings.memory_path)
    sessions = data.setdefault("sessions", {})
    turns = sessions.setdefault(session_id, [])
    turns.append(
        {
            "run_id": state.get("run_id"),
            "query": state.get("query"),
            "answer": (state.get("verified_answer") or state.get("draft_answer") or "")[:800],
            "confidence": (state.get("validation") or {}).get("confidence"),
            "sources": sorted(
                {
                    d.get("source", "")
                    for d in (state.get("retrieved_docs") or [])
                    if d.get("source")
                }
            ),
        }
    )
    # keep last 20 turns per session
    sessions[session_id] = turns[-20:]
    _save(settings.memory_path, data)
    return {
        "traces": [
            trace("memory", "stored", f"session={session_id}; turns={len(sessions[session_id])}")
        ]
    }
