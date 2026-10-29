"""Retriever agent: multi-query RAG over Chroma."""

from __future__ import annotations

from typing import Any

from knowledge_ops.config import get_settings
from knowledge_ops.eval_logging import trace
from knowledge_ops.ingest import get_chroma_collection
from knowledge_ops.llm import get_embeddings
from knowledge_ops.state import KnowledgeOpsState, RetrievedDoc


def _search(query: str, top_k: int) -> list[RetrievedDoc]:
    settings = get_settings()
    collection = get_chroma_collection(settings)
    embeddings = get_embeddings(settings)
    vector = embeddings.embed_query(query)
    count = collection.count()
    if count == 0:
        return []
    n = min(top_k, count)
    result = collection.query(
        query_embeddings=[vector],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    docs: list[RetrievedDoc] = []
    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for i, doc_id in enumerate(ids):
        dist = float(distances[i]) if i < len(distances) else 1.0
        # Chroma distance → similarity-ish score
        score = 1.0 / (1.0 + dist)
        meta = metadatas[i] if i < len(metadatas) else {}
        docs.append(
            RetrievedDoc(
                id=str(doc_id),
                text=documents[i] if i < len(documents) else "",
                source=str(meta.get("source", "unknown")),
                score=round(score, 4),
                metadata=dict(meta) if meta else {},
            )
        )
    return docs


def retrieve_node(state: KnowledgeOpsState) -> dict[str, Any]:
    settings = get_settings()
    if state.get("refused"):
        return {"traces": [trace("retriever", "skipped", "request refused")]}

    queries = state.get("sub_queries") or [state.get("query") or ""]
    merged: dict[str, RetrievedDoc] = {}
    for q in queries:
        for doc in _search(q, settings.retrieval_top_k):
            existing = merged.get(doc["id"])
            if existing is None or float(doc.get("score") or 0) > float(
                existing.get("score") or 0
            ):
                merged[doc["id"]] = doc

    ranked = sorted(merged.values(), key=lambda d: float(d.get("score") or 0), reverse=True)
    # Cap overall context size
    ranked = ranked[: settings.retrieval_top_k * 2]
    sources = sorted({d.get("source", "") for d in ranked})
    return {
        "retrieved_docs": ranked,
        "traces": [
            trace(
                "retriever",
                "retrieved",
                f"queries={len(queries)}; chunks={len(ranked)}; sources={sources}",
            )
        ],
    }
