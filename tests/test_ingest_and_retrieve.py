from knowledge_ops.agents.retriever import retrieve_node
from knowledge_ops.ingest import ingest_documents, load_documents
from knowledge_ops.llm import MockEmbeddings, resolve_provider


def test_sample_docs_present():
    from knowledge_ops.config import get_settings

    docs = load_documents(get_settings().docs_dir)
    assert len(docs) >= 3
    names = {name for name, _ in docs}
    assert "hr_remote_work_policy.md" in names


def test_ingest_creates_chunks(tmp_settings):
    result = ingest_documents(settings=tmp_settings, reset=True)
    assert result["documents"] >= 3
    assert result["chunks"] > 0


def test_mock_provider_selected(tmp_settings):
    assert resolve_provider(tmp_settings) == "mock"


def test_mock_embeddings_deterministic():
    emb = MockEmbeddings(dim=32)
    a = emb.embed_query("remote work hybrid policy")
    b = emb.embed_query("remote work hybrid policy")
    c = emb.embed_query("totally unrelated expense receipt rules")
    assert a == b
    assert a != c


def test_retriever_returns_docs(tmp_settings):
    ingest_documents(settings=tmp_settings, reset=True)
    state = {
        "query": "What is the hybrid remote work schedule?",
        "sub_queries": ["hybrid remote work schedule", "remote work policy eligibility"],
        "refused": False,
    }
    out = retrieve_node(state)
    assert out["retrieved_docs"]
    assert any("remote" in (d.get("source") or "").lower() or "remote" in (d.get("text") or "").lower()
               for d in out["retrieved_docs"])
