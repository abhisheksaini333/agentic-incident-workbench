import threading
from http.server import HTTPServer
import httpx
from model.server import handler


def test_worker_rejects_unauthorized_and_unbounded_requests_without_inference():
    class Fake:
        calls = 0

        def generate(self, prompt, maximum):
            self.calls += 1
            return {"text": "none"}

    model = Fake()
    server = HTTPServer(
        ("127.0.0.1", 0), handler(model, "private-model-key-long-enough")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = "http://127.0.0.1:" + str(server.server_address[1])
        assert httpx.post(origin + "/generate", json={"prompt": "x"}).status_code == 403
        headers = {"Authorization": "Bearer private-model-key-long-enough"}
        assert (
            httpx.post(
                origin + "/generate",
                headers=headers,
                json={"prompt": "x", "max_new_tokens": 999},
            ).status_code
            == 400
        )
        assert model.calls == 0
        assert (
            httpx.post(
                origin + "/generate", headers=headers, json={"prompt": "x"}
            ).status_code
            == 200
        )
        assert model.calls == 1
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
