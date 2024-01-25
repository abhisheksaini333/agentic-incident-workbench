import pytest
from incident.store import Store
from incident.domain import new_incident
from incident.identity import Actor


def test_reclaimed_lease_rejects_old_worker_even_with_same_owner():
    s = Store()
    i = s.create(
        new_incident(
            Actor("acme", "alice", frozenset({"operator"})), "checkout", "Errors", 0
        )
    )
    old = s.claim("acme", i["id"], "worker", 0, seconds=1)
    new = s.claim("acme", i["id"], "worker", 2, seconds=60)
    with pytest.raises(ValueError, match="lease"):
        s.worker_update(
            "acme", i["id"], old["lease"], 3, lambda x: x.update(title="stale")
        )
    saved = s.worker_update(
        "acme", i["id"], new["lease"], 3, lambda x: x.update(title="current")
    )
    assert saved["title"] == "current"
    with pytest.raises(ValueError, match="lease"):
        s.worker_update(
            "acme", i["id"], new["lease"], 62, lambda x: x.update(title="expired")
        )
