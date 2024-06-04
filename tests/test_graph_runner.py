from engine_support import engine_case
from incident.engine import Engine
from incident.graph import GraphRunner


def test_graph_pauses_for_review_then_resumes_persisted_cursor_without_duplicate_work():
    store, flow, incident, operator, reviewer, simulator, tools = engine_case()
    key = incident["id"]
    runner = GraphRunner(Engine(store, tools, clock=lambda: 10))
    first = runner.run_until_pause("acme", key)
    assert first["status"] == "awaiting_approval"
    assert first["budget"]["effects"] == 0
    second = GraphRunner(Engine(store, tools, clock=lambda: 10)).run_until_pause(
        "acme", key
    )
    assert second["revision"] == first["revision"]
    flow.approve(reviewer, key, first["plan"]["digest"], first["revision"], 10)
    done = GraphRunner(Engine(store, tools, clock=lambda: 11)).run_until_pause(
        "acme", key
    )
    assert done["status"] == "resolved"
    assert len(done["receipts"]) == 1
    again = runner.run_until_pause("acme", key)
    assert again["revision"] == done["revision"]
