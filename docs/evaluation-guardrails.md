# Evaluation & Guardrails

How the Enterprise Knowledge Ops Agent measures quality, blocks unsafe inputs, and records observability signals.

## Guardrails

### Input validation (`knowledge_ops/guardrails.py`)

| Check | Behavior |
|-------|----------|
| Empty / whitespace query | Refuse with reason |
| Length > 2000 chars | Refuse |
| Jailbreak / instruction-override patterns | Refuse; flag `guardrail_triggered` |
| (Future) ACL / sensitivity labels | Out of scope for this case study |

Refusals short-circuit retrieval and still emit eval + trace records via the Orchestrator finalize path.

### Output grounding (Verifier)

For each draft answer the Verifier computes:

- **Citation presence** — `[source:file#id]` markers
- **Claim support** — lexical overlap of sentences against retrieved chunks
- **Grounding score** — blend of support ratio, lexical overlap, citation bonus
- **Confidence** — currently equal to grounding score (LLM self-score can replace/mock-augment later)
- **Flags** — `ungrounded_claim`, `missing_citations`, `low_confidence`, `insufficient_context`, `narrow_retrieval`, `guardrail_triggered`

If confidence is below `CONFIDENCE_THRESHOLD` (default `0.55`), the graph may retry Analyst once, then return a **limited answer** with disclaimers.

### Attribution & disclaimers

Every response includes:

- Source list (id, filename, score, excerpt)
- Standard disclaimer that answers are retrieval-based
- Extra warnings when grounding is weak or context is insufficient

## Evaluation metrics

Structured rows append to `logs/eval.jsonl` (one JSON object per run):

| Field | Meaning |
|-------|---------|
| `run_id` / `session_id` / `query` | Identity |
| `latency_ms` | End-to-end wall time |
| `retrieval_count` | Chunks returned after merge |
| `unique_sources` | Distinct filenames |
| `grounding_score` / `confidence` / `grounded` | Verifier outcomes |
| `flags` | Guardrail / quality flags |
| `pass` | `grounded` and not `low_confidence` |
| `refused` | Input guardrail blocked the query |
| `verify_attempts` / `sub_query_count` | Orchestration depth |

Decision traces land in `logs/traces/<run_id>.json` with plan, retrieved excerpts, draft/verified answers, validation, and agent event timeline.

## Failure detection

| Symptom | Signal |
|---------|--------|
| No corpus ingested | `retrieval_count=0`, flag `insufficient_context` |
| Hallucinated claim | `ungrounded_claim`, lower `grounding_score` |
| Thin evidence | `narrow_retrieval` |
| Prompt injection attempt | `refused=true`, `guardrail_triggered` |
| Weak answer after retry | Limited-answer suffix + `low_confidence` |

## Rubric mapping

| Rubric area | Mechanism |
|-------------|-----------|
| Validation, grounding & guardrails | Verifier + input filters + disclaimers |
| Evaluation & observability | `eval.jsonl`, trace files, UI/CLI trace panels |
| Retrieval effectiveness | Multi-query Chroma search, source diversity in logs |
| Reasoning quality | Analyst synthesis constrained to evidence |

## Manual eval checklist

1. Ingest sample docs (`python -m app.cli ingest --reset`).
2. Ask a single-doc question (e.g. hybrid schedule) — expect citations + `pass≈true`.
3. Ask a cross-doc question (expense approvals + IT access SLA) — expect ≥2 unique sources when retrieval works.
4. Ask an out-of-corpus question — expect insufficient-context / low confidence.
5. Ask a jailbreak-style prompt — expect refusal.

Automated coverage lives in repo unit tests; see [unit-tests.md](./unit-tests.md).
