import pytest
from incident.simulator import Simulator


def test_injected_failure_survives_restart_and_other_tenants_remain_healthy(tmp_path):
    path = tmp_path / "simulator.db"
    s = Simulator(path)
    s.provision("acme", "checkout")
    s.provision("beta", "checkout")
    result = s.inject("acme", "checkout", ["disk_pressure"], variant=1)
    assert result["generation"] == 2 and not result["healthy"]
    s.close()
    s = Simulator(path)
    assert s.observe("acme", "checkout")["metrics"]["disk_percent"] == 99
    assert s.observe("beta", "checkout")["healthy"]
    with pytest.raises(LookupError):
        s.observe("acme", "unknown")
    with pytest.raises(ValueError):
        s.inject("acme", "checkout", ["arbitrary_failure"])
    s.close()
