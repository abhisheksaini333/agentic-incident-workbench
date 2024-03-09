import pytest
from incident.effects import EffectJournal
from incident.simulator import Simulator
from incident.workflow import Workflow
from incident.identity import Actor
from journal_support import approved_incident


class Client:
    def __init__(self, simulator):
        self.simulator = simulator
        self.calls = 0

    def receipt(self, tenant, service, key):
        return self.simulator.receipt(tenant, key)

    def apply(self, *args):
        self.calls += 1
        return self.simulator.apply(*args)


def test_lost_receipt_recovers_after_restart_without_duplicate_effect(tmp_path):
    from incident.store import Store

    path = tmp_path / "incidents.db"
    s, w, i = approved_incident(Store(path))
    j = EffectJournal(s)
    sim = Simulator(tmp_path / "sim.db")
    sim.provision("acme", "checkout")
    sim.inject("acme", "checkout", ["memory_pressure"])
    client = Client(sim)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)

    def crash():
        raise SystemExit("worker crashed after external effect")

    with pytest.raises(SystemExit):
        j.dispatch(entry, i["lease"], client, 4, after_effect=crash)
    assert client.calls == 1 and not s.get("acme", i["id"])["receipts"]
    s.close()
    s = Store(path)
    j = EffectJournal(s)
    receipt = j.dispatch(entry, i["lease"], client, 5)
    assert client.calls == 1 and receipt["effect_number"] == 1
    assert len(s.get("acme", i["id"])["receipts"]) == 1 and not j.pending(
        "acme", i["id"]
    )


def test_late_receipt_can_be_reconciled_after_cancellation_but_new_effect_cannot():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    sim = Simulator()
    sim.provision("acme", "checkout")
    sim.inject("acme", "checkout", ["memory_pressure"])
    c = Client(sim)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)
    receipt = sim.apply(
        "acme", "checkout", entry["step"], entry["key"], entry["generation"]
    )
    current = s.get("acme", i["id"])
    w.cancel(
        Actor("acme", "alice", frozenset({"operator"})), i["id"], current["revision"], 4
    )
    assert j.reconcile(entry, c, 5) == receipt
    assert s.get("acme", i["id"])["status"] == "cancelled" and c.calls == 0
