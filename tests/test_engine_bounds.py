import time
from incident.engine import Engine
from incident.budgets import Limits
from engine_support import engine_case


def test_step_budget_stops_before_unbounded_progress():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    result = Engine(s, tools, limits=Limits(steps=2), clock=lambda: 10).run_until_pause(
        "acme", i["id"]
    )
    assert result["checkpoint"] == "plan"
    result = Engine(s, tools, limits=Limits(steps=2), clock=lambda: 10).tick(
        "acme", i["id"]
    )
    assert result["status"] == "escalated" and result["receipts"] == []


def test_failed_tool_latency_is_still_charged():
    s, f, i, operator, reviewer, sim, tools = engine_case()

    class Broken:
        def observe(self, *args):
            time.sleep(0.02)
            raise ConnectionError("unavailable")

    result = Engine(s, Broken(), clock=lambda: 10).tick("acme", i["id"])
    assert result["status"] == "escalated" and result["budget"]["seconds"] >= 0.02
