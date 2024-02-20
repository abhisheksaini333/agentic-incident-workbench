import pytest
from incident.domain import new_incident
from incident.identity import Actor
from incident.postgres import PostgresStore


def test_separate_postgres_connections_preserve_versions_and_lease_fences(pgstore):
    first = pgstore
    second = PostgresStore(first.url, first.schema)
    try:
        incident = first.create(
            new_incident(
                Actor("acme", "alice", frozenset({"operator"})),
                "checkout",
                "Failure",
                0,
            )
        )
        old = first.claim("acme", incident["id"], "one", 0, seconds=1)
        new = second.claim("acme", incident["id"], "two", 2)
        with pytest.raises(ValueError, match="lease"):
            first.worker_update(
                "acme",
                incident["id"],
                old["lease"],
                3,
                lambda x: x.update(checkpoint="incorrect"),
            )
        second.worker_update(
            "acme",
            incident["id"],
            new["lease"],
            3,
            lambda x: x.update(checkpoint="diagnose"),
        )
        assert first.get("acme", incident["id"])["checkpoint"] == "diagnose"
        with pytest.raises(LookupError):
            second.get("beta", incident["id"])
    finally:
        second.close()
