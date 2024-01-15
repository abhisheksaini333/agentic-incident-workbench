import pytest
from incident.store import Store
from incident.domain import new_incident
from incident.identity import Actor


def test_incidents_survive_reopen_and_stale_writes_do_not_replace_state(tmp_path):
    path = tmp_path / "incidents.db"
    actor = Actor("acme", "alice", frozenset({"operator"}))
    store = Store(path)
    incident = store.create(new_incident(actor, "checkout", "Errors", 1))
    changed = store.mutate(
        "acme",
        incident["id"],
        lambda x: x.update(title="Investigating"),
        expected_revision=1,
    )
    assert changed["revision"] == 2
    with pytest.raises(ValueError, match="revision"):
        store.mutate(
            "acme",
            incident["id"],
            lambda x: x.update(title="stale"),
            expected_revision=1,
        )
    store.close()
    reopened = Store(path)
    assert reopened.get("acme", incident["id"])["title"] == "Investigating"
    with pytest.raises(LookupError):
        reopened.get("beta", incident["id"])
    reopened.close()
