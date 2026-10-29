# Unit Test Cases

Runnable tests live in the repository under `tests/`. They default to the **mock LLM/embeddings** provider so CI and local demos need no API keys.

## How to run

```bash
cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -q
```

Fixtures in `tests/conftest.py` isolate Chroma, logs, and memory under a temp directory and force `LLM_PROVIDER=mock`.

## Test inventory

### Guardrails — `tests/test_guardrails.py`

| Case | Intent |
|------|--------|
| `test_validate_input_rejects_empty` | Empty queries fail closed |
| `test_validate_input_blocks_jailbreak` | Injection / jailbreak patterns blocked |
| `test_validate_input_accepts_normal_query` | Legitimate business questions pass |
| `test_verify_grounding_flags_insufficient_context` | No docs → `insufficient_context` |
| `test_verify_grounding_with_citations` | Cited, overlapping answer scores confidence |

### Ingest & retrieval — `tests/test_ingest_and_retrieve.py`

| Case | Intent |
|------|--------|
| `test_sample_docs_present` | Sample enterprise corpus is available |
| `test_ingest_creates_chunks` | Chunking + Chroma upsert produces vectors |
| `test_mock_provider_selected` | Auto/fallback selects mock without keys |
| `test_mock_embeddings_deterministic` | Offline embeddings are stable |
| `test_retriever_returns_docs` | Multi-query retrieval returns relevant chunks |

### Planning — `tests/test_orchestrator_plan.py`

| Case | Intent |
|------|--------|
| `test_parse_plan_extracts_sub_queries` | Plan parser reads SUB_QUERIES block |
| `test_parse_plan_fallback_when_empty` | Degenerate LLM output still yields a plan |
| `test_mock_chat_plan_and_answer` | Mock LLM produces plan + grounded-style answer |
| `test_orchestrate_creates_plan` | Orchestrator node emits plan + run id |

### Graph / E2E — `tests/test_graph.py`

| Case | Intent |
|------|--------|
| `test_end_to_end_grounded_query` | Full graph returns answer, sources, traces, eval JSONL |
| `test_cross_document_query` | Complex query exercises multi-step plan/retrieval |
| `test_guardrail_refusal` | Harmful prompt refused with flag |
| `test_memory_persists_across_turns` | Memory agent stores multi-turn session state |

## Acceptance mapping

| User story | Covered by |
|------------|------------|
| Complex query handling | `test_cross_document_query`, retriever tests |
| Planning & orchestration | orchestrator plan tests + E2E traces |
| Grounded responses | grounding tests + E2E validation fields |
| Explainability | E2E asserts traces + trace file path |
| Governance | input refusal + disclaimer path in E2E |
| Evaluation & observability | `eval.jsonl` assertion in E2E |

## Notes

- Tests do **not** call Azure/OpenAI. To smoke-test a live provider, set keys from `.env.example` and run `python -m app.cli query "..."`.
- Chroma persistence directories created during tests are under pytest `tmp_path` and discarded automatically.
