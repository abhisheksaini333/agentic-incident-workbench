import pytest
from incident.evidence import snapshot

def test_evidence_envelope_version_and_health_are_explicit():
    valid=dict(generation=1,healthy=False,metrics={},logs=[])
    for payload in [None,[],{**valid,"healthy":"false"},{**valid,"healthy":1}]:
        with pytest.raises(ValueError): snapshot(payload,1)
    for version in [True,1.5,"1"]:
        with pytest.raises(ValueError): snapshot(valid,version)
    assert snapshot(valid,1)["healthy"] is False
