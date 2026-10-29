"""Shared LangGraph state for the Knowledge Ops agent."""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


class RetrievedDoc(TypedDict, total=False):
    id: str
    text: str
    source: str
    score: float
    metadata: dict[str, Any]


class TraceEvent(TypedDict, total=False):
    agent: str
    event: str
    detail: str
    ts: str


class ValidationResult(TypedDict, total=False):
    grounded: bool
    confidence: float
    flags: list[str]
    unsupported_claims: list[str]
    grounding_score: float


def _merge_traces(
    left: list[TraceEvent] | None, right: list[TraceEvent] | None
) -> list[TraceEvent]:
    return (left or []) + (right or [])


class KnowledgeOpsState(TypedDict, total=False):
    query: str
    session_id: str
    run_id: str
    sub_queries: list[str]
    plan: dict[str, Any]
    retrieved_docs: list[RetrievedDoc]
    draft_answer: str
    verified_answer: str
    validation: ValidationResult
    memory_context: str
    traces: Annotated[list[TraceEvent], _merge_traces]
    eval_log: dict[str, Any]
    disclaimers: list[str]
    verify_attempts: int
    refused: bool
    refusal_reason: str
    final_response: dict[str, Any]
