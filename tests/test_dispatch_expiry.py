import time
import pytest
from incident.effects import EffectJournal
from journal_support import approved_incident


def test_slow_receipt_lookup_cannot_extend_expired_dispatch_authority():
    s, w, i = approved_incident()
    j = EffectJournal(s)
    entry = j.prepare("acme", i["id"], i["lease"], 0, 3)

    class Slow:
        calls = 0

        def receipt(self, *args):
            time.sleep(0.04)
            return None

        def apply(self, *args):
            self.calls += 1
            raise AssertionError("Must not dispatch")

    client = Slow()
    with pytest.raises(ValueError, match="lease"):
        j.dispatch(entry, i["lease"], client, 61.99)
    assert client.calls == 0
