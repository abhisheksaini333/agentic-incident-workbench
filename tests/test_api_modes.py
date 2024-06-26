from api_support import api_fixture
from fastapi.testclient import TestClient
from incident.api import create_app


def test_model_incidents_require_configured_worker_and_mode_is_persisted():
    store, auth, client, headers = api_fixture()
    operator = headers("operator")
    data = {"service": "checkout", "title": "Graph diagnosis", "mode": "graph"}
    assert client.post("/api/incidents", headers=operator, json=data).status_code == 503
    configured = TestClient(create_app(store, auth, model_enabled=True))
    result = configured.post("/api/incidents", headers=operator, json=data)
    assert result.status_code == 201 and result.json()["mode"] == "graph"
    assert configured.get("/api/config").json()["modes"] == ["rules", "single", "graph"]
    assert (
        configured.post(
            "/api/incidents", headers=operator, json={**data, "mode": "unbounded"}
        ).status_code
        == 422
    )
