import httpx
import pytest
from incident.simulator_client import SimulatorClient


def test_client_binds_paths_and_treats_stale_evidence_as_nonretryable():
    requests = []

    def reply(request):
        requests.append(request)
        return httpx.Response(409, json={"detail": "Service evidence is stale"})

    client = SimulatorClient(
        "http://localhost:8086",
        "private-worker-key",
        transport=httpx.MockTransport(reply),
    )
    with pytest.raises(ValueError, match="recollect"):
        client.apply(
            "acme",
            "checkout",
            {"action": "restart_service", "target": "checkout", "arguments": {}},
            "effect-key-123456",
            3,
        )
    assert requests[0].url.path == "/v1/acme/checkout/effects"
    with pytest.raises(ValueError):
        client.observe("../beta", "checkout")
    assert len(requests) == 1
