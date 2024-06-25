import pytest
from engine_support import engine_case
from incident.runners import runner_for
from incident.graph import GraphRunner


def test_graph_mode_uses_real_graph_and_missing_model_fails_safely():
    store, flow, _, operator, _, _, tools = engine_case()
    item = flow.create(operator, "checkout", "Graph incident", 1, mode="graph")
    runner = runner_for(store, tools, item)
    assert isinstance(runner, GraphRunner)
    result = runner.run_until_pause("acme", item["id"])
    assert result["status"] == "escalated"
    assert result["budget"]["effects"] == 0
    assert result["error"] == "RuntimeError"
