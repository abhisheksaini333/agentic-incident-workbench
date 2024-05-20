from incident.effects import EffectJournal
from incident.engine import Engine
from incident.worker import Worker
from incident.simulator import Simulator
from incident.identity import Actor
from journal_support import approved_incident


def test_receipt_outage_does_not_block_other_incidents_or_repeat_an_effect():
    s, flow, i = approved_incident()
    journal = EffectJournal(s)
    entry = journal.prepare("acme", i["id"], i["lease"], 0, 3)
    sim = Simulator()
    sim.provision("acme", "checkout")
    sim.inject("acme", "checkout", ["memory_pressure"])
    existing = sim.apply(
        "acme", "checkout", entry["step"], entry["key"], entry["generation"]
    )
    other = flow.create(
        Actor("acme", "alice", frozenset({"operator"})),
        "checkout",
        "Unrelated incident",
        1,
    )

    class Client:
        broken = True
        applies = 0

        def receipt(self, tenant, service, key):
            if self.broken:
                raise ConnectionError("simulator unavailable")
            return sim.receipt(tenant, key)

        def observe(self, *args):
            return sim.observe(*args)

        def workload(self, *args):
            return sim.workload(*args)

        def apply(self, *args):
            self.applies += 1
            return sim.apply(*args)

    client = Client()
    now = [100]
    worker = Worker(
        s, lambda _: Engine(s, client, clock=lambda: now[0]), clock=lambda: now[0]
    )
    assert worker.once()
    deferred = s.get("acme", i["id"])
    assert deferred["retry_at"] == 102 and deferred["transport_failures"] == 1
    assert s.get("acme", other["id"])["status"] == "resolved"
    assert len(journal.pending("acme", i["id"])) == 1 and deferred["receipts"] == []
    client.broken = False
    now[0] = 103
    assert worker.once()
    final = s.get("acme", i["id"])
    assert final["status"] == "resolved" and len(final["receipts"]) == 1
    assert (
        final["receipts"][0]["effect_number"] == existing["effect_number"] == 1
        and client.applies == 0
    )


def test_transport_retries_escalate_after_three_failures_without_erasing_outbox():
    s, flow, i = approved_incident()
    journal = EffectJournal(s)
    journal.prepare("acme", i["id"], i["lease"], 0, 3)
    for now in [100, 102, 106]:
        s.defer_transport("acme", i["id"], now)
    stopped = s.get("acme", i["id"])
    assert (
        stopped["status"] == "escalated" and stopped["error"] == "receipt_unavailable"
    )
    assert len(journal.pending("acme", i["id"])) == 1
