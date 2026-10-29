"""Optional Streamlit UI for queries, sources, and decision traces."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from knowledge_ops.config import get_settings
from knowledge_ops.graph import run_query
from knowledge_ops.ingest import ingest_documents
from knowledge_ops.llm import resolve_provider

st.set_page_config(page_title="Knowledge Ops Agent", layout="wide")
st.title("Enterprise Knowledge Ops Agent")
st.caption("LangGraph multi-agent RAG — planning, retrieval, analysis, verification, memory")

settings = get_settings()
with st.sidebar:
    st.header("Controls")
    st.write(f"**LLM provider:** `{resolve_provider()}`")
    st.write(f"**Chroma:** `{settings.chroma_dir}`")
    session_id = st.text_input("Session ID", value="ui-session")
    if st.button("Ingest sample docs", use_container_width=True):
        with st.spinner("Ingesting..."):
            result = ingest_documents(reset=True)
        st.success(
            f"Ingested {result['documents']} docs / {result['chunks']} chunks"
        )

query = st.text_area(
    "Question",
    placeholder="e.g. What is the hybrid work baseline and how do expense approvals work above $500?",
    height=120,
)
ask = st.button("Ask", type="primary")

if ask and query.strip():
    with st.spinner("Running multi-agent graph..."):
        result = run_query(query.strip(), session_id=session_id)

    col1, col2 = st.columns([1.4, 1])
    with col1:
        st.subheader("Answer")
        st.write(result.get("answer", ""))
        validation = result.get("validation") or {}
        st.subheader("Validation")
        st.json(validation)
        st.subheader("Disclaimers")
        for d in result.get("disclaimers") or []:
            st.write(f"- {d}")
    with col2:
        st.subheader("Sources")
        for s in result.get("sources") or []:
            st.markdown(f"**{s.get('source')}** · score `{s.get('score')}`")
            st.write(s.get("excerpt", ""))
        st.subheader("Plan")
        st.json(result.get("plan") or {})
        st.subheader("Traces")
        for t in result.get("traces") or []:
            st.text(f"{t.get('agent')}/{t.get('event')}: {t.get('detail')}")
        if result.get("trace_path"):
            st.caption(f"Trace file: {result['trace_path']}")
elif ask:
    st.warning("Enter a question first.")
