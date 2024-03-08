from incident.store import Store
from incident.workflow import Workflow
from incident.identity import Actor
from incident.evidence import snapshot
from incident.plans import make_plan


def approved_incident(store=None):
    s = store or Store()
    operator = Actor("acme", "alice", frozenset({"operator"}))
    reviewer = Actor("acme", "bob", frozenset({"approver"}))
    s.add_account(
        {
            "tenant": "acme",
            "subject": "bob",
            "roles": ["approver"],
            "password_hash": "unused",
        }
    )
    w = Workflow(s)
    i = w.create(operator, "checkout", "Failure", 0)

    def prepare(x):
        x["status"] = "awaiting_approval"
        x["plan_sequence"] = 1
        x["evidence"] = snapshot(
            {"generation": 2, "metrics": {}, "logs": [], "healthy": False}, 1
        )
        x["plan"] = make_plan(
            x,
            x["evidence"],
            [{"action": "restart_service", "target": "checkout", "arguments": {}}],
            "alice",
            1,
            "Restart leaking process",
        )

    i = s.mutate("acme", i["id"], prepare)
    i = w.approve(reviewer, i["id"], i["plan"]["digest"], i["revision"], 1)
    i = s.claim("acme", i["id"], "worker", 2)
    return s, w, i
