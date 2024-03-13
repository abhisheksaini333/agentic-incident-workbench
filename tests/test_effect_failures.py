import pytest
from incident.effects import EffectJournal
from journal_support import approved_incident


class FailingClient:
    def receipt(self, *args):
        return None

    def apply(self, *args):
        raise ConnectionError("lost transport")


def test_failed_transport_attempts_remain_bounded_durably():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)
    client = FailingClient()
    for moment in [4, 5, 6]:
        with pytest.raises(ConnectionError):
            j.dispatch(entry, i["lease"], client, moment)
    with pytest.raises(ValueError, match="retry budget"):
        j.dispatch(entry, i["lease"], client, 7)
    assert j.pending("acme", i["id"])[0]["attempts"] == 3


def test_receipt_with_invalid_effect_number_never_enters_incident_history():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)
    receipt = {
        "key": entry["key"],
        "request_digest": entry["request_digest"],
        "action": "restart_service",
        "generation_before": 2,
        "generation_after": 3,
        "changed": True,
        "effect_number": 0,
    }

    class Client:
        def receipt(self, *args):
            return receipt

    with pytest.raises(ValueError, match="receipt"):
        j.reconcile(entry, Client(), 4)
    assert s.get("acme", i["id"])["receipts"] == []
