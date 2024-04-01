from incident.engine import Engine
from engine_support import engine_case


def test_recovery_requires_both_health_and_workload_success():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    engine = Engine(s, tools, clock=lambda: 10)
    for _ in range(3):
        result = engine.tick("acme", i["id"])
    f.approve(reviewer, i["id"], result["plan"]["digest"], result["revision"], 11)
    engine.tick("acme", i["id"])
    result = engine.tick("acme", i["id"])
    assert result["status"] == "resolved" and len(result["evidence_history"]) == 2
    assert len(result["receipts"]) == 1 and result["evidence"]["healthy"]
