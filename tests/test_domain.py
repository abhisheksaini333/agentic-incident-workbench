import pytest
from incident.domain import new_incident, transition
from incident.identity import Actor


def test_incident_has_a_bounded_explicit_lifecycle():
    actor = Actor("acme", "alice", frozenset({"operator"}))
    incident = new_incident(actor, "checkout", "Checkout returns errors", now=10)
    assert incident["status"] == "new" and incident["revision"] == 1
    changed = transition(incident, "collecting")
    assert changed["status"] == "collecting" and incident["status"] == "new"
    with pytest.raises(ValueError):
        transition(incident, "resolved")
    with pytest.raises(ValueError):
        new_incident(actor, "checkout", " ", now=10)
