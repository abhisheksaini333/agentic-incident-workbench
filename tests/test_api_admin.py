from api_support import api_fixture


def test_admin_role_updates_are_tenant_scoped_and_apply_to_existing_tokens():
    store, auth, c, headers = api_fixture()
    admin = headers("admin")
    operator = headers("operator")
    assert (
        c.put(
            "/api/accounts/operator/roles", headers=operator, json={"roles": []}
        ).status_code
        == 403
    )
    assert (
        c.put(
            "/api/accounts/outsider/roles", headers=admin, json={"roles": []}
        ).status_code
        == 404
    )
    assert (
        c.put(
            "/api/accounts/operator/roles", headers=admin, json={"roles": []}
        ).status_code
        == 200
    )
    assert c.get("/api/me", headers=operator).status_code == 401
    assert c.delete("/api/session", headers=operator).status_code == 200
    assert (
        c.post(
            "/api/simulation",
            headers=headers("viewer"),
            json={"service": "checkout", "faults": []},
        ).status_code
        == 403
    )
