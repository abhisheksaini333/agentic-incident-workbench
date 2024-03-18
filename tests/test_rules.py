from incident.diagnosis import RulesPolicy, supported
from incident.evidence import snapshot
from incident.scenarios import observation, healthy_state


def test_baseline_identifies_compound_signals_and_ignores_unsupported_labels():
    state = healthy_state()
    state["faults"] = ["disk_pressure", "queue_backlog"]
    evidence = snapshot(observation(state), 1)
    results = RulesPolicy().diagnose(evidence)
    assert {r["label"] for r in results} == {"disk_pressure", "queue_backlog"}
    assert all(r["references"] for r in results)
    assert not supported("bad_release", evidence)
    assert RulesPolicy().diagnose(snapshot(observation(healthy_state()), 1)) == []
