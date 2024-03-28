from incident.engine import Engine
from engine_support import engine_case


def test_later_evidence_does_not_erase_a_prior_plan_snapshot():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    engine = Engine(s, tools, clock=lambda: 1)
    for _ in range(3):
        result = engine.tick("acme", i["id"])
    original = result["evidence"]["digest"]
    f.retry(operator, i["id"], result["revision"], 2)
    sim.inject("acme", "checkout", ["disk_pressure"])
    result = engine.tick("acme", i["id"])
    assert len(result["evidence_history"]) == 2
    assert result["evidence_history"][0]["digest"] == original
    assert (
        result["evidence"]["version"] == 2 and result["evidence"]["digest"] != original
    )
