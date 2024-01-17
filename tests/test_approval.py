import pytest
from incident.approval import review, approved
from incident.identity import Actor
from incident.plans import make_plan


def fixture():
    incident = {
        "id": "incident",
        "tenant": "acme",
        "service": "checkout",
        "status": "awaiting_approval",
        "evidence": {"version": 1, "generation": 1, "digest": "evidence"},
    }
    incident["plan"] = make_plan(
        incident,
        incident["evidence"],
        [{"action": "restart_service", "target": "checkout", "arguments": {}}],
        "alice",
        1,
        "Restart the leaking process",
    )
    return incident


def test_exact_approval_expires_and_cannot_be_self_or_stale():
    incident = fixture()
    actor = Actor("acme", "bob", frozenset({"approver"}))
    incident["approval"] = review(incident, actor, incident["plan"]["digest"], now=10)
    assert approved(incident, now=11)
    assert not approved(incident, now=611)
    with pytest.raises(PermissionError):
        review(
            incident,
            Actor("acme", "alice", frozenset({"approver"})),
            incident["plan"]["digest"],
            10,
        )
    with pytest.raises(ValueError):
        review(incident, actor, "stale digest", 10)
    incident["evidence"]["digest"] = "new evidence"
    assert not approved(incident, now=12)
