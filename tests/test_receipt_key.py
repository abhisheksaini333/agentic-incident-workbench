import pytest
from incident.simulator_client import SimulatorClient


def test_receipt_key_is_validated_before_any_network_call():
    client = SimulatorClient("http://unreachable.local", "worker-secret")
    for key in ["../observe", "../../other/effects/123", "a" * 120]:
        with pytest.raises(ValueError, match="receipt key"):
            client.receipt("acme", "checkout", key)
    client.close()
