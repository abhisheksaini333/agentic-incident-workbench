from incident.domain import new_incident
from incident.identity import Actor
from incident.store import Store
from incident.workflow import Workflow


def test_recollection_does_not_reuse_a_previous_plan_sequence():
    actor = Actor("acme", "alice", frozenset({"operator"}))
    s = Store()
    w = Workflow(s)
    i = w.create(actor, "checkout", "Failure", 0)
    assert i["plan_sequence"] == 0
    i = s.mutate(
        "acme", i["id"], lambda x: x.update(status="escalated", plan_sequence=4)
    )
    retried = w.retry(actor, i["id"], i["revision"], 1)
    assert retried["plan_sequence"] == 4
