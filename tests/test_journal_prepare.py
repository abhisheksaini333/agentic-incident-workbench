import pytest
from incident.effects import EffectJournal
from journal_support import approved_incident


def test_preparation_is_idempotent_and_binds_plan_evidence_and_step():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    first = j.prepare("acme", i["id"], i["lease"], 0, 3)
    assert first == j.prepare("acme", i["id"], i["lease"], 0, 4)
    assert len(j.pending("acme", i["id"])) == 1
    assert s.get("acme", i["id"])["budget"]["effects"] == 1
    s.set_roles("acme", "bob", ["viewer"])
    with pytest.raises(PermissionError):
        j.prepare("acme", i["id"], i["lease"], 0, 5)
