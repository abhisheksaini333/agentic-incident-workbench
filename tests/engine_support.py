from incident.store import Store
from incident.workflow import Workflow
from incident.identity import Actor
from incident.simulator import Simulator


def engine_case(faults=None, store=None):
    s = store or Store()
    operator = Actor("acme", "alice", frozenset({"operator"}))
    reviewer = Actor("acme", "bob", frozenset({"approver"}))
    s.add_account(
        {
            "tenant": "acme",
            "subject": "alice",
            "roles": ["operator"],
            "password_hash": "unused",
        }
    )
    s.add_account(
        {
            "tenant": "acme",
            "subject": "bob",
            "roles": ["approver"],
            "password_hash": "unused",
        }
    )
    sim = Simulator()
    sim.provision("acme", "checkout")
    sim.inject("acme", "checkout", faults or ["memory_pressure"])
    flow = Workflow(s)
    incident = flow.create(operator, "checkout", "Service requests fail", 0)

    class Client:
        def observe(self, *args):
            return sim.observe(*args)

        def receipt(self, tenant, service, key):
            return sim.receipt(tenant, key)

        def apply(self, *args):
            return sim.apply(*args)

        def workload(self, *args):
            return sim.workload(*args)

    return s, flow, incident, operator, reviewer, sim, Client()
