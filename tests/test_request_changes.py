import pytest
from incident.engine import Engine
from engine_support import engine_case


def test_requested_changes_block_approval_until_a_new_plan_is_reviewed():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    result = Engine(s, tools, clock=lambda: 10).run_until_pause("acme", i["id"])
    rejected = f.request_changes(
        reviewer, i["id"], result["revision"], "Explain the restart blast radius", 11
    )
    with pytest.raises(ValueError, match="change request"):
        f.approve(
            reviewer, i["id"], rejected["plan"]["digest"], rejected["revision"], 12
        )
    edited = f.edit(
        operator,
        i["id"],
        rejected["plan"]["steps"],
        "Restart affects only this simulated service",
        rejected["revision"],
        13,
    )
    assert edited["review_request"] is None
    accepted = f.approve(
        reviewer, i["id"], edited["plan"]["digest"], edited["revision"], 14
    )
    assert accepted["status"] == "approved" and accepted["plan"]["version"] == 2
