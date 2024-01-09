import pytest
from incident.evidence import snapshot


def test_evidence_digest_binds_generation_and_rejects_nonfinite_metrics():
    payload = {
        "generation": 1,
        "metrics": {"cpu_percent": 80.0},
        "logs": ["workers busy"],
        "healthy": False,
    }
    first = snapshot(payload, 1)
    assert first["digest"] == snapshot(payload, 1)["digest"]
    payload["generation"] = 2
    assert snapshot(payload, 1)["digest"] != first["digest"]
    assert first["observations"][0]["reference"] == "metric:cpu_percent"
    payload["metrics"]["cpu_percent"] = float("nan")
    with pytest.raises(ValueError):
        snapshot(payload, 2)
