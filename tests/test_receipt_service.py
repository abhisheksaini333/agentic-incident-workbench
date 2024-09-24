from fastapi.testclient import TestClient
from incident.simulator import Simulator
from incident.simulator_api import create_simulator_app


def test_a_receipt_cannot_be_read_through_another_service_path():
    sim = Simulator()
    sim.provision("acme", "checkout")
    sim.provision("acme", "different")
    before = sim.inject("acme", "checkout", ["memory_pressure"])
    sim.apply(
        "acme",
        "checkout",
        {"action": "restart_service", "target": "checkout", "arguments": {}},
        "effect-key-123456",
        before["generation"],
    )
    client = TestClient(
        create_simulator_app(
            sim, "worker-secret-long-enough", "admin-secret-long-enough"
        )
    )
    headers = {"Authorization": "Bearer worker-secret-long-enough"}
    assert (
        client.get(
            "/v1/acme/checkout/effects/effect-key-123456", headers=headers
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/v1/acme/different/effects/effect-key-123456", headers=headers
        ).status_code
        == 404
    )
