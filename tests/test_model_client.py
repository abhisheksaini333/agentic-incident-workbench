import httpx
import pytest
from incident.model_client import ModelClient


def test_model_client_has_fixed_authority_and_rejects_forged_usage():
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "text": "memory_pressure",
                "input_tokens": 55,
                "output_tokens": 4,
                "revision": "371f99f1df1429771f01227c93bd662f5eec2480",
            },
        )

    client = ModelClient("http://model.local", "k" * 24, httpx.MockTransport(respond))
    assert client.generate("Classify evidence")["output_tokens"] == 4
    assert seen[0].headers["Authorization"] == "Bearer " + "k" * 24
    client.close()
    bad = ModelClient(
        "http://model.local",
        "k" * 24,
        httpx.MockTransport(
            lambda r: httpx.Response(
                200,
                json={
                    "text": "x",
                    "input_tokens": -1,
                    "output_tokens": 999,
                    "revision": "wrong",
                },
            )
        ),
    )
    with pytest.raises(ValueError):
        bad.generate("x")
    with pytest.raises(ValueError):
        ModelClient("http://user:pass@model.local", "k" * 24)
