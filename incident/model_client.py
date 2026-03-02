from urllib.parse import urlparse
import httpx

REVISION = "371f99f1df1429771f01227c93bd662f5eec2480"


class ModelClient:
    def __init__(self, origin, key, transport=None):
        parsed = urlparse(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or len(key) < 24
        ):
            raise ValueError("Configure a fixed model origin and private key")
        self.client = httpx.Client(
            base_url=origin,
            timeout=30,
            transport=transport,
            headers={"Authorization": "Bearer " + key},
        )

    def generate(self, prompt):
        if not isinstance(prompt, str) or not 1 <= len(prompt) <= 8000:
            raise ValueError("Model prompt exceeds its bound")
        response = self.client.post(
            "/generate", json={"prompt": prompt, "max_new_tokens": 48}
        )
        response.raise_for_status()
        if len(response.content) > 16384:
            raise ValueError("Model response exceeds its bound")
        result = response.json()
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("text"), str)
            or len(result["text"]) > 2000
            or result.get("revision") != REVISION
            or type(result.get("input_tokens")) is not int
            or not 1 <= result["input_tokens"] <= 512
            or type(result.get("output_tokens")) is not int
            or not 0 <= result["output_tokens"] <= 48
        ):
            raise ValueError("Invalid model identity or token accounting")
        return {
            name: result[name]
            for name in ["text", "input_tokens", "output_tokens", "revision"]
        }

    def close(self):
        self.client.close()
