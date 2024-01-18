import pytest
from incident.store import Store
from incident.identity import Actor
from incident.workflow import Workflow
from incident.evidence import snapshot
from incident.plans import make_plan


def test_human_edit_replaces_plan_version_and_clears_approval():
    store = Store()
    flow = Workflow(store)
    operator = Actor("acme", "alice", frozenset({"operator"}))
    reviewer = Actor("acme", "bob", frozenset({"approver"}))
    i = flow.create(operator, "checkout", "Errors", 1)

    def prepare(x):
        x["status"] = "awaiting_approval"
        x["evidence"] = snapshot(
            {"generation": 1, "metrics": {}, "logs": [], "healthy": False}, 1
        )
        x["plan"] = make_plan(
            x,
            x["evidence"],
            [{"action": "restart_service", "target": "checkout", "arguments": {}}],
            "alice",
            1,
            "Restart",
        )

    i = store.mutate("acme", i["id"], prepare)
    i = flow.approve(reviewer, i["id"], i["plan"]["digest"], i["revision"], 2)
    changed = flow.edit(
        operator,
        i["id"],
        [
            {
                "action": "rotate_logs",
                "target": "checkout",
                "arguments": {"keep_files": 2},
            }
        ],
        "Disk evidence suggests rotation",
        i["revision"],
        3,
    )
    assert changed["status"] == "awaiting_approval" and changed["plan"]["version"] == 2
    assert changed["approval"] is None
    with pytest.raises(ValueError):
        flow.approve(reviewer, i["id"], i["plan"]["digest"], changed["revision"], 4)
