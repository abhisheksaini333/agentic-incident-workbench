from incident.budgets import Limits
from incident.engine import Engine
from engine_support import engine_case


def test_run_returns_a_terminal_budget_outcome_instead_of_an_active_orphan():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    result = Engine(s, tools, limits=Limits(steps=2), clock=lambda: 10).run_until_pause(
        "acme", i["id"]
    )
    assert result["status"] == "escalated" and result["checkpoint"] == "complete"
    assert (
        result["budget"]["steps"] == 2
        and not sim.observe("acme", "checkout")["healthy"]
    )
