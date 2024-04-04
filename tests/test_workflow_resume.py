import pytest
from incident.identity import Actor
from incident.effects import EffectJournal
from journal_support import approved_incident


def test_resume_retains_plan_outbox_and_consumed_budget():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)
    stopped = s.mutate(
        "acme", i["id"], lambda x: x.update(status="escalated", lease=None)
    )
    actor = Actor("acme", "alice", frozenset({"operator"}))
    resumed = w.resume(actor, i["id"], stopped["revision"], 4)
    assert resumed["plan"]["digest"] == entry["plan_digest"]
    assert resumed["checkpoint"] == "execute" and resumed["budget"]["effects"] == 1
    stopped = s.mutate("acme", i["id"], lambda x: x.update(status="escalated"))
    with pytest.raises(ValueError):
        w.resume(actor, i["id"], stopped["revision"], 900)
