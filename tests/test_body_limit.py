from fastapi.testclient import TestClient
from fastapi import FastAPI
from incident.http_limits import BodyLimitMiddleware


def test_body_limit_checks_actual_stream_size_without_trusting_header():
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware, limit=20)

    @app.post("/")
    def accept(body: dict):
        return body

    client = TestClient(app)
    assert (
        client.post(
            "/", content='{"x":"' + "a" * 40 + '"}', headers={"Content-Length": "1"}
        ).status_code
        == 413
    )
    assert client.post("/", json={"x": "ok"}).status_code == 200
