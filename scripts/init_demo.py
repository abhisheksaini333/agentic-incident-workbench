"""Create a private local demo environment without overwriting existing secrets."""
import os
from pathlib import Path
import secrets


def initialize(path):
    password = secrets.token_hex(24)
    values = {
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": "postgresql://incident:"
        + password
        + "@localhost:54385/incident",
        "JWT_SECRET": secrets.token_hex(32),
        "SIMULATOR_URL": "http://localhost:8086",
        "SIMULATOR_KEY": secrets.token_hex(24),
        "SIMULATOR_ADMIN_KEY": secrets.token_hex(24),
        "MODEL_URL": "http://localhost:8087",
        "MODEL_KEY": secrets.token_hex(24),
        "MODEL_DIR": "models/flan-t5-small",
        "ENABLE_MODEL_MODES": "0",
        "DEMO_PASSWORD": secrets.token_urlsafe(18),
        "SIMULATOR_DB": "data/simulator.db",
    }
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("".join(key + "=" + value + "\n" for key, value in values.items()))
    return Path(path)


if __name__ == "__main__":
    initialize(".env")
    print("Created private .env. Keep its DEMO_PASSWORD for the local sign-in form.")
