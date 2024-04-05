from fastapi.testclient import TestClient
from incident.store import Store
from incident.auth import AuthManager
from incident.api import create_app


def api_fixture():
    store = Store()
    auth = AuthManager(store, "a-private-test-secret-" * 3)
    for tenant, subject, role in [
        ("acme", "operator", "operator"),
        ("acme", "reviewer", "approver"),
        ("acme", "viewer", "viewer"),
        ("acme", "admin", "admin"),
        ("beta", "outsider", "operator"),
    ]:
        auth.create_account(tenant, subject, "a-long-local-password", [role])
    client = TestClient(create_app(store, auth))

    def headers(subject):
        response = client.post(
            "/api/session",
            json={"subject": subject, "password": "a-long-local-password"},
        )
        assert response.status_code == 200
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    return store, auth, client, headers
