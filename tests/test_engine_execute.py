from incident.engine import Engine
from engine_support import engine_case


def test_multi_action_plan_runs_in_order_and_retains_one_receipt_per_effect():
    s, f, i, operator, reviewer, sim, tools = engine_case(
        ["disk_pressure", "queue_backlog"]
    )
    engine = Engine(s, tools, clock=lambda: 10)
    for _ in range(3):
        result = engine.tick("acme", i["id"])
    f.approve(reviewer, i["id"], result["plan"]["digest"], result["revision"], 11)
    first = engine.tick("acme", i["id"])
    assert first["status"] == "executing" and len(first["receipts"]) == 1
    second = engine.tick("acme", i["id"])
    assert second["status"] == "verifying" and len(second["receipts"]) == 2
    assert (
        second["receipts"][1]["generation_before"]
        == second["receipts"][0]["generation_after"]
    )
    assert sim.observe("acme", "checkout")["healthy"]


def test_revoked_reviewer_prevents_a_previously_approved_effect():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    engine = Engine(s, tools, clock=lambda: 10)
    for _ in range(3):
        result = engine.tick("acme", i["id"])
    f.approve(reviewer, i["id"], result["plan"]["digest"], result["revision"], 11)
    s.set_roles("acme", "bob", ["viewer"])
    result = engine.tick("acme", i["id"])
    assert result["status"] == "escalated" and result["receipts"] == []
    assert not sim.observe("acme", "checkout")["healthy"]
