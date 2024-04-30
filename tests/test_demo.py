from incident.demo import seed_demo, SERVICES
from incident.auth import AuthManager
from incident.store import Store
from incident.simulator import Simulator


def test_seed_does_not_overwrite_accounts_or_recovered_services():
    s = Store()
    auth = AuthManager(s, "x" * 48)
    sim = Simulator()
    result = seed_demo(auth, sim, "a-long-local-password")
    assert result["accounts_created"] == 8 and len(SERVICES) == 6
    auth.store.set_roles("acme", "acme.viewer", [])
    current = sim.observe("acme", "heap-api")
    sim.apply(
        "acme",
        "heap-api",
        {"action": "restart_service", "target": "heap-api", "arguments": {}},
        "effect-key-123456",
        current["generation"],
    )
    assert seed_demo(auth, sim, "a-long-local-password")["accounts_created"] == 0
    assert sim.observe("acme", "heap-api")["healthy"]
    assert auth.store.account("acme.viewer")["roles"] == []
