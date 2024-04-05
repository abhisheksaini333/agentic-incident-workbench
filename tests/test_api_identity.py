from api_support import api_fixture


def test_incident_reads_and_creation_enforce_current_roles_and_tenants():
    store, auth, c, headers = api_fixture()
    operator = headers("operator")
    viewer = headers("viewer")
    outsider = headers("outsider")
    assert c.get("/api/me").status_code == 401
    assert (
        c.post(
            "/api/incidents",
            headers=viewer,
            json={"service": "checkout", "title": "Failure"},
        ).status_code
        == 403
    )
    created = c.post(
        "/api/incidents",
        headers=operator,
        json={"service": "checkout", "title": "Failure"},
    )
    assert created.status_code == 201
    key = created.json()["id"]
    assert c.get("/api/incidents/" + key, headers=viewer).status_code == 200
    assert c.get("/api/incidents/" + key, headers=outsider).status_code == 404
    assert c.get("/api/incidents", headers=outsider).json()["incidents"] == []
    assert c.delete("/api/session", headers=operator).status_code == 200
    assert c.get("/api/me", headers=operator).status_code == 401
