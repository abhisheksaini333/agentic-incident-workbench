from fastapi.testclient import TestClient
from incident.api import create_app
from incident.auth import AuthManager
from incident.store import Store


def test_console_assets_do_not_shadow_protected_api_routes(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Incident console</h1>")
    s = Store()
    c = TestClient(create_app(s, AuthManager(s, "x" * 48), frontend_dir=tmp_path))
    assert c.get("/").status_code == 200 and "Incident console" in c.get("/").text
    assert c.get("/api/me").status_code == 401
    assert c.get("/api/config").json()["modes"] == ["rules"]
