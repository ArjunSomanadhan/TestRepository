"""LangGraph wiring for the Knowledge Ops multi-agent system."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from knowledge_ops.agents.analyst import analyze_node
from knowledge_ops.agents.memory import memory_load_node, memory_store_node
from knowledge_ops.agents.orchestrator import finalize_node, orchestrate_node
from knowledge_ops.agents.retriever import retrieve_node
from knowledge_ops.agents.verifier import should_retry_analysis, verify_node
from knowledge_ops.eval_logging import Timer, new_run_id
from knowledge_ops.state import KnowledgeOpsState

_GRAPH = None


def _route_after_orchestrate(state: KnowledgeOpsState) -> str:
    if state.get("refused"):
        return "finalize"
    return "memory_load"


def build_graph():
    graph = StateGraph(KnowledgeOpsState)
    graph.add_node("orchestrate", orchestrate_node)
    graph.add_node("memory_load", memory_load_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("verify", verify_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("memory_store", memory_store_node)

    graph.add_edge(START, "orchestrate")
    graph.add_conditional_edges(
        "orchestrate",
        _route_after_orchestrate,
        {"memory_load": "memory_load", "finalize": "finalize"},
    )
    graph.add_edge("memory_load", "retrieve")
    graph.add_edge("retrieve", "analyze")
    graph.add_edge("analyze", "verify")
    graph.add_conditional_edges(
        "verify",
        should_retry_analysis,
        {"analyze": "analyze", "finalize": "finalize"},
    )
    graph.add_edge("finalize", "memory_store")
    graph.add_edge("memory_store", END)
    return graph.compile()


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def reset_graph() -> None:
    global _GRAPH
    _GRAPH = None


def run_query(
    query: str,
    *,
    session_id: str = "default",
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute the full Knowledge Ops graph and return the final response envelope."""
    timer = Timer()
    graph = get_graph()
    initial: KnowledgeOpsState = {
        "query": query,
        "session_id": session_id,
        "run_id": run_id or new_run_id(),
        "traces": [],
        "verify_attempts": 0,
    }
    final_state = graph.invoke(initial)
    # Ensure latency recorded if finalize didn't get it
    response = final_state.get("final_response")
    if not response:
        from knowledge_ops.eval_logging import build_final_response, write_trace_file

        path = write_trace_file(final_state)
        response = build_final_response(final_state, trace_path=str(path))
    response["latency_ms"] = round(timer.ms(), 2)
    response["state_summary"] = {
        "sub_queries": final_state.get("sub_queries"),
        "validation": final_state.get("validation"),
        "retrieval_count": len(final_state.get("retrieved_docs") or []),
    }
    return response
