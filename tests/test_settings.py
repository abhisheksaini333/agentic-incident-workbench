import pytest
from incident.settings import Settings


def test_runtime_rejects_short_keys_and_credential_bearing_tool_urls():
    with pytest.raises(ValueError):
        Settings(jwt_secret="short", simulator_key="x" * 32)
    with pytest.raises(ValueError):
        Settings(
            jwt_secret="x" * 32,
            simulator_key="y" * 32,
            simulator_url="http://user:secret@localhost:8086",
        )
    valid = Settings(jwt_secret="x" * 32, simulator_key="y" * 32)
    assert valid.simulator_url == "http://localhost:8086"
