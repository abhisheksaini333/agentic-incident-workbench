from incident.engine import Engine
from engine_support import engine_case


def test_planning_pauses_durably_and_does_not_remediate_without_approval():
    s, f, i, operator, reviewer, sim, tools = engine_case(
        ["disk_pressure", "queue_backlog"]
    )
    engine = Engine(s, tools, clock=lambda: 1)
    for _ in range(3):
        result = engine.tick("acme", i["id"])
    assert result["status"] == "awaiting_approval" and len(result["plan"]["steps"]) == 2
    assert result["plan"]["evidence_digest"] == result["evidence"]["digest"]
    assert engine.tick("acme", i["id"]) == result
    assert not sim.observe("acme", "checkout")["healthy"] and result["receipts"] == []
