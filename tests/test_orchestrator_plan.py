from knowledge_ops.agents.orchestrator import _parse_plan, orchestrate_node
from knowledge_ops.llm import MockChatModel


def test_parse_plan_extracts_sub_queries():
    raw = """PLAN:
1. Retrieve remote policy
2. Synthesize
SUB_QUERIES:
- hybrid remote schedule
- remote stipend amount
"""
    plan, subs = _parse_plan(raw, "fallback query")
    assert len(plan["steps"]) >= 2
    assert "hybrid remote schedule" in subs
    assert "remote stipend amount" in subs


def test_parse_plan_fallback_when_empty():
    plan, subs = _parse_plan("no structure here", "expense approval matrix")
    assert plan["steps"]
    assert any("expense" in s.lower() for s in subs)


def test_mock_chat_plan_and_answer():
    model = MockChatModel()
    plan = model.invoke("Plan the following. Decompose into sub-queries.\nUser question: remote hybrid days")
    assert "SUB_QUERIES" in plan
    answer = model.invoke(
        "Question: hybrid schedule\n"
        "[source:hr.md#1]\nDefault hybrid schedule is 3 days in office / 2 days remote.\n"
    )
    assert "source:" in answer.lower() or "hybrid" in answer.lower()


def test_orchestrate_creates_plan(tmp_settings):
    out = orchestrate_node({"query": "What is the SEV-1 notification requirement?"})
    assert out["refused"] is False
    assert out["sub_queries"]
    assert out["plan"]["steps"]
    assert out["run_id"]
