import pytest
from incident.domain import new_incident
from incident.identity import Actor
from incident.store import Store
from incident.workflow import Workflow


def test_cancellation_revokes_lease_and_retains_receipts_and_budget():
    actor = Actor("acme", "alice", frozenset({"operator"}))
    s = Store()
    f = Workflow(s)
    i = f.create(actor, "checkout", "Failure", 0)
    claimed = s.claim("acme", i["id"], "worker", 0)
    i = s.worker_update(
        "acme",
        i["id"],
        claimed["lease"],
        1,
        lambda x: x.update(receipts=[{"key": "already-applied"}]),
    )
    cancelled = f.cancel(actor, i["id"], i["revision"], 2)
    assert (
        cancelled["receipts"] == [{"key": "already-applied"}]
        and cancelled["lease"] is None
    )
    with pytest.raises(ValueError, match="lease"):
        s.worker_update(
            "acme", i["id"], claimed["lease"], 3, lambda x: x.update(status="resolved")
        )


def test_recollect_keeps_evidence_version_and_used_budget_for_stale_detection():
    actor = Actor("acme", "alice", frozenset({"operator"}))
    s = Store()
    f = Workflow(s)
    i = f.create(actor, "checkout", "Failure", 0)
    i = s.mutate(
        "acme",
        i["id"],
        lambda x: x.update(
            status="escalated", evidence={"version": 3}, budget={"steps": 20}
        ),
    )
    next = f.retry(actor, i["id"], i["revision"], 1)
    assert (
        next["checkpoint"] == "collect"
        and next["evidence"]["version"] == 3
        and next["budget"]["steps"] == 20
    )
