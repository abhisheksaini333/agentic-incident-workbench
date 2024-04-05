from api_support import api_fixture
from incident.evidence import snapshot
from incident.plans import make_plan


def test_http_approval_rejects_wrong_role_and_stale_digest():
    store, auth, c, headers = api_fixture()
    op = headers("operator")
    reviewer = headers("reviewer")
    incident = c.post(
        "/api/incidents", headers=op, json={"service": "checkout", "title": "Failure"}
    ).json()

    def prepare(x):
        x["status"] = "awaiting_approval"
        x["evidence"] = snapshot(
            {"generation": 1, "metrics": {}, "logs": [], "healthy": False}, 1
        )
        x["plan"] = make_plan(
            x,
            x["evidence"],
            [{"action": "restart_service", "target": "checkout", "arguments": {}}],
            "operator",
            1,
            "Restart",
        )

    incident = store.mutate("acme", incident["id"], prepare)
    path = "/api/incidents/" + incident["id"] + "/approve"
    body = {"revision": incident["revision"], "digest": incident["plan"]["digest"]}
    assert c.post(path, headers=op, json=body).status_code == 403
    assert (
        c.post(path, headers=reviewer, json={**body, "digest": "f" * 64}).status_code
        == 409
    )
    result = c.post(path, headers=reviewer, json=body)
    assert result.status_code == 200 and result.json()["status"] == "approved"
    assert c.post(path, headers=reviewer, json=body).status_code == 409
