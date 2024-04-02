from incident.store import Store
from incident.domain import new_incident
from incident.identity import Actor


def test_reclaim_accounts_for_time_lost_when_a_worker_crashes():
    s = Store()
    i = s.create(
        new_incident(
            Actor("acme", "alice", frozenset({"operator"})), "checkout", "Failure", 0
        )
    )
    s.claim("acme", i["id"], "crashed", 10, seconds=5)
    reclaimed = s.claim("acme", i["id"], "replacement", 30, seconds=5)
    assert reclaimed["budget"]["seconds"] == 5
    assert reclaimed["lease"]["started_at"] == 30
