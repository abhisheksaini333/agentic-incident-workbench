"""Isolated original FLAN-T5 inference worker; no tools or database authority."""
import argparse
import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import time

REVISION = "371f99f1df1429771f01227c93bd662f5eec2480"


def verify_files(directory, manifest):
    for item in manifest:
        path = directory / item["file"]
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise ValueError(
                "Model file is missing or has the wrong size: " + item["file"]
            )
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != item["sha256"]:
            raise ValueError("Model integrity mismatch: " + item["file"])


class Flan:
    def __init__(self, directory):
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(directory), local_files_only=True
        )
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            str(directory), local_files_only=True
        )
        self.model.eval()

    def generate(self, prompt, maximum):
        encoded = self.tokenizer(prompt, return_tensors="pt", truncation=False)
        count = encoded["input_ids"].shape[1]
        if count > 512:
            raise ValueError("Prompt exceeds the 512-token model context")
        with self.torch.inference_mode():
            output = self.model.generate(
                **encoded, max_new_tokens=maximum, do_sample=False, num_beams=1
            )
        # The decoder starts with one non-generated start token.
        return {
            "text": self.tokenizer.decode(output[0], skip_special_tokens=True),
            "input_tokens": count,
            "output_tokens": max(0, output.shape[1] - 1),
            "revision": REVISION,
        }


def handler(model, key):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, format, *args):
            # Request credentials and prompt text are never included in logs.
            pass

        def send_json(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.send_json(
                200 if self.path == "/health" else 404,
                {"ready": True, "revision": REVISION}
                if self.path == "/health"
                else {"error": "Not found"},
            )

        def do_POST(self):
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + key
            ):
                return self.send_json(403, {"error": "Model worker authority required"})
            if self.path != "/generate":
                return self.send_json(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 16000:
                    raise ValueError("Request size exceeds the bound")
                body = json.loads(self.rfile.read(length))
                prompt, maximum = body.get("prompt"), body.get("max_new_tokens", 48)
                if not isinstance(prompt, str) or not 1 <= len(prompt) <= 8000:
                    raise ValueError("Invalid prompt length")
                if type(maximum) is not int or not 1 <= maximum <= 48:
                    raise ValueError("Invalid generation bound")
                start = time.monotonic()
                result = model.generate(prompt, maximum)
                self.send_json(200, {**result, "seconds": time.monotonic() - start})
            except (ValueError, TypeError, json.JSONDecodeError):
                self.send_json(400, {"error": "Invalid bounded model request"})
            except Exception:
                self.send_json(503, {"error": "Model inference unavailable"})

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8087)
    parser.add_argument(
        "--directory", default=os.getenv("MODEL_DIR", "models/flan-t5-small")
    )
    args = parser.parse_args()
    key = os.getenv("MODEL_KEY", "")
    if len(key) < 24:
        raise ValueError("Set a private MODEL_KEY of at least 24 characters")
    directory = Path(args.directory)
    manifest = json.loads(
        (Path(__file__).resolve().parents[1] / "models/manifest.json").read_text()
    )
    verify_files(directory, manifest)
    server = HTTPServer((args.host, args.port), handler(Flan(directory), key))
    print("Original FLAN-T5 worker ready", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
