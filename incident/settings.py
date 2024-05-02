from dataclasses import dataclass
import os
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///data/incidents.db"
    jwt_secret: str = ""
    simulator_url: str = "http://localhost:8086"
    simulator_key: str = ""
    simulator_admin_key: str = ""

    def __post_init__(self):
        if len(self.jwt_secret) < 32 or len(self.simulator_key) < 24:
            raise ValueError("Set private JWT_SECRET and SIMULATOR_KEY values")
        parsed = urlparse(self.simulator_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Simulator URL must be an HTTP origin without credentials, query or fragment"
            )

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.getenv("DATABASE_URL", cls.database_url),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            simulator_url=os.getenv("SIMULATOR_URL", cls.simulator_url),
            simulator_key=os.getenv("SIMULATOR_KEY", ""),
            simulator_admin_key=os.getenv("SIMULATOR_ADMIN_KEY", ""),
        )
