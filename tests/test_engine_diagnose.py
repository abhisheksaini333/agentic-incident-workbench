from incident.engine import Engine
from engine_support import engine_case


def test_diagnosis_uses_current_signals_and_unsupported_claims_escalate():
    s, f, i, operator, reviewer, sim, tools = engine_case(["disk_pressure"])
    engine = Engine(s, tools, clock=lambda: 1)
    engine.tick("acme", i["id"])
    result = engine.tick("acme", i["id"])
    assert (
        result["checkpoint"] == "plan"
        and result["hypotheses"][0]["label"] == "disk_pressure"
    )

    class Unfounded:
        name = "fixture"

        def diagnose(self, evidence):
            return [{"label": "memory_pressure", "references": ["log:invented"]}]

    s, f, i, *rest = engine_case(["disk_pressure"])
    tools = rest[-1]
    engine = Engine(s, tools, Unfounded(), clock=lambda: 1)
    engine.tick("acme", i["id"])
    assert engine.tick("acme", i["id"])["status"] == "escalated"
