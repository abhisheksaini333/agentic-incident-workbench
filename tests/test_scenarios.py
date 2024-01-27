from incident.scenarios import FAULTS, observation, healthy_state


def test_fault_families_have_distinct_signals_without_exposing_hidden_labels():
    assert len(FAULTS) == 6
    for fault in FAULTS:
        state = healthy_state()
        state["faults"] = [fault]
        evidence = observation(state)
        assert not evidence["healthy"] and evidence["metrics"]["error_rate"] > 0
        assert "faults" not in evidence and evidence["logs"]
    assert observation(healthy_state())["healthy"]
