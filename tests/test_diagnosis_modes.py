import pytest
from engine_support import engine_case


def test_mode_is_validated_and_persisted_with_bounded_progress():
    store, flow, _, operator, *_ = engine_case()
    item = flow.create(operator, "checkout", "Investigate", 1, mode="graph")
    assert item["mode"] == "graph"
    assert item["model_results"] == []
    with pytest.raises(ValueError):
        flow.create(operator, "checkout", "Investigate", 1, mode="unbounded")
