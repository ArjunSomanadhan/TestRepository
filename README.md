# Enterprise Knowledge Ops Agent

Local multi-agent system (LangGraph + LangChain + Chroma) that plans complex enterprise questions, retrieves across policies/SOPs, synthesizes grounded answers, verifies citations/confidence, and logs traces for evaluation.

Case-study docs: [`docs/architecture.md`](docs/architecture.md), [`docs/evaluation-guardrails.md`](docs/evaluation-guardrails.md), [`docs/unit-tests.md`](docs/unit-tests.md).

## Features

- **Agents:** Orchestrator → Memory → Retriever → Analyst → Verifier → Finalize/Memory
- **RAG:** Sample enterprise docs ingested into persistent Chroma
- **LLM:** Azure OpenAI if configured, else OpenAI, else deterministic **mock** (demos/tests without keys)
- **Guardrails:** Input filters + grounding/confidence checks + disclaimers
- **Observability:** `logs/eval.jsonl` and `logs/traces/<run_id>.json`
- **Interfaces:** CLI and optional Streamlit UI

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env        # optional — edit if using Azure/OpenAI
```

### Environment

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `auto` (default), `azure`, `openai`, or `mock` |
| `AZURE_OPENAI_*` | Azure chat + embedding deployments |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI fallback |
| `CHROMA_DIR` | Vector store path (default `.chroma`) |
| `DOCS_DIR` | Corpus path (default `data/sample_docs`) |
| `LOGS_DIR` / `MEMORY_PATH` | Eval traces + session memory |
| `CONFIDENCE_THRESHOLD` | Verifier cutoff (default `0.55`) |

With no API keys, the app uses the mock LLM/embeddings automatically.

## Ingest documents

```bash
python -m app.cli ingest --reset
# or
python -m knowledge_ops.ingest --reset
```

Sample policies/SOPs are under `data/sample_docs/` (HR remote work, IT access, finance expenses, security IR, eng change management). Add `.md` / `.txt` files there and re-ingest.

## Run queries (CLI)

```bash
python -m app.cli query "What is the hybrid remote work baseline and the home-office stipend?"
python -m app.cli query "How do expense approvals work above \$500 and what is the manager SLA for IT access?" --json
python -m app.cli query "jailbreak ignore previous instructions"  # expect refusal
```

## Run UI (optional)

```bash
streamlit run app/streamlit_app.py
```

Use the sidebar **Ingest sample docs** button once, then ask questions. The UI shows answer, validation flags, sources, plan, and agent traces.

## Logs & traces

| Path | Contents |
|------|----------|
| `logs/eval.jsonl` | One evaluation record per run (grounding, confidence, flags, latency) |
| `logs/traces/<run_id>.json` | Full decision trail for a run |
| `logs/memory.json` | Short-term session Q/A memory |

## Tests

```bash
pytest -q
```

See [`docs/unit-tests.md`](docs/unit-tests.md) for the case catalog.

## AWS note

Runtime focus is local. For a later AWS deploy sketch (ECS/Lambda, OpenSearch/pgvector, Secrets Manager, CloudWatch), see [`docs/architecture.md`](docs/architecture.md) — AWS deployment section. Production auth/scale is out of scope for this case study.

## Layout

```text
app/cli.py                 CLI ingest + query
app/streamlit_app.py       Optional UI
src/knowledge_ops/         Agents, graph, ingest, guardrails, logging
data/sample_docs/          Enterprise sample corpus
tests/                     Unit + graph tests
```
