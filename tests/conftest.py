"""Shared fixtures for Knowledge Ops tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def tmp_settings(tmp_path, monkeypatch):
    docs = ROOT / "data" / "sample_docs"
    chroma = tmp_path / "chroma"
    logs = tmp_path / "logs"
    memory = logs / "memory.json"
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("CHROMA_DIR", str(chroma))
    monkeypatch.setenv("DOCS_DIR", str(docs))
    monkeypatch.setenv("LOGS_DIR", str(logs))
    monkeypatch.setenv("MEMORY_PATH", str(memory))
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.55")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from knowledge_ops import config, llm, graph

    # Force settings / LLM / graph caches to rebuild
    llm.reset_llm_cache()
    graph.reset_graph()
    settings = config.get_settings()
    yield settings
    llm.reset_llm_cache()
    graph.reset_graph()
