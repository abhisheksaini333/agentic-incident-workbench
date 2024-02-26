from incident.simulator import Simulator


def test_receipt_lookup_is_read_only_and_tenant_scoped():
    s = Simulator()
    s.provision("acme", "checkout")
    observed = s.inject("acme", "checkout", ["disk_pressure"])
    key = "effect-key-123456"
    assert s.receipt("acme", key) is None
    first = s.apply(
        "acme",
        "checkout",
        {"action": "rotate_logs", "target": "checkout", "arguments": {"keep_files": 2}},
        key,
        observed["generation"],
    )
    assert s.receipt("acme", key) == first and s.receipt("beta", key) is None
    assert s.observe("acme", "checkout")["generation"] == first["generation_after"]
