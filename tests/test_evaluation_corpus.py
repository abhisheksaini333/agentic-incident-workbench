import json
from pathlib import Path
from incident.scenarios import FAULTS


def test_comparison_fixture_keeps_calibration_and_held_out_cases_disjoint():
    corpus = json.loads(Path("fixtures/evaluation.json").read_text())
    training = corpus["calibration"]
    held = corpus["held_out"]
    assert {x["id"] for x in training}.isdisjoint({x["id"] for x in held})
    assert len(held) == 11
    assert {name for x in held for name in x["faults"]} == set(FAULTS)
    assert any(not x["faults"] for x in held)
    assert any(len(x["faults"]) == 3 for x in held)
    assert all(x["variant"] == 1 for x in held)
