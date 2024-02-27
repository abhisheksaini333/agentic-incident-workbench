from fastapi.testclient import TestClient
from incident.simulator import Simulator
from incident.simulator_api import create_simulator_app


def test_simulator_requires_separate_injection_authority_and_recovers_over_http():
    c = TestClient(
        create_simulator_app(
            Simulator(), "worker-secret-long-enough", "admin-secret-long-enough"
        )
    )
    admin = {"Authorization": "Bearer admin-secret-long-enough"}
    worker = {"Authorization": "Bearer worker-secret-long-enough"}
    path = "/v1/acme/checkout"
    assert c.post(path + "/provision", headers=worker).status_code == 403
    assert c.post(path + "/provision", headers=admin).status_code == 200
    assert c.get(path + "/observe").status_code == 403
    assert (
        c.post(
            path + "/faults", headers=worker, json={"faults": ["bad_release"]}
        ).status_code
        == 403
    )
    before = c.post(
        path + "/faults", headers=admin, json={"faults": ["bad_release"]}
    ).json()
    assert c.get(path + "/workload", headers=worker).status_code == 503
    response = c.post(
        path + "/effects",
        headers=worker,
        json={
            "key": "effect-key-123456",
            "generation": before["generation"],
            "step": {
                "action": "rollback_release",
                "target": "checkout",
                "arguments": {"release": "stable"},
            },
        },
    )
    assert response.status_code == 200
    assert c.get(path + "/workload", headers=worker).status_code == 200
    assert (
        c.get(path + "/metrics", headers=worker)
        .headers["content-type"]
        .startswith("text/plain")
    )
