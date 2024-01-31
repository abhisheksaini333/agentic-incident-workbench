import pytest
from incident.simulator import Simulator
from incident.scenarios import FAULTS


def test_response_loss_replay_never_duplicates_effects(tmp_path):
    path = tmp_path / "sim.db"
    s = Simulator(path)
    s.provision("acme", "checkout")
    before = s.inject("acme", "checkout", ["memory_pressure"])
    step = {"action": "restart_service", "target": "checkout", "arguments": {}}
    first = s.apply("acme", "checkout", step, "effect-key-123456", before["generation"])
    s.close()
    s = Simulator(path)
    replay = s.apply(
        "acme", "checkout", step, "effect-key-123456", before["generation"]
    )
    assert (
        replay == first
        and replay["effect_number"] == 1
        and s.observe("acme", "checkout")["healthy"]
    )
    with pytest.raises(ValueError, match="bound"):
        s.apply(
            "acme", "checkout", step, "effect-key-123456", first["generation_after"]
        )
    with pytest.raises(ValueError, match="stale"):
        s.apply("acme", "checkout", step, "different-key-12345", before["generation"])


@pytest.mark.parametrize("fault", list(FAULTS))
def test_each_allowed_remediation_recovers_only_its_fault(fault):
    s = Simulator()
    s.provision("acme", "checkout")
    before = s.inject("acme", "checkout", [fault])
    spec = FAULTS[fault]
    receipt = s.apply(
        "acme",
        "checkout",
        {
            "action": spec["action"],
            "target": "checkout",
            "arguments": spec["arguments"],
        },
        "effect-key-123456",
        before["generation"],
    )
    assert receipt["changed"] and s.observe("acme", "checkout")["healthy"]
