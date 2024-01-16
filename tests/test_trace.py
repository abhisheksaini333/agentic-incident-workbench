import pytest
from incident.store import Store
from incident.domain import new_incident
from incident.identity import Actor
from incident.trace import append_event


def test_queue_is_tenant_scoped_and_trace_rejects_unbounded_payloads():
    store = Store()
    a = new_incident(Actor("acme", "a", frozenset({"operator"})), "checkout", "A", 1)
    b = new_incident(Actor("beta", "b", frozenset({"operator"})), "checkout", "B", 2)
    store.create(a)
    store.create(b)
    assert [x["id"] for x in store.list("acme")] == [a["id"]]
    append_event(
        a,
        "observed",
        "operator",
        "Collected service evidence",
        3,
        ["metric:cpu_percent"],
    )
    assert a["trace"][0]["references"] == ["metric:cpu_percent"]
    with pytest.raises(ValueError):
        append_event(a, "bad", "operator", "x" * 2000, 4)
