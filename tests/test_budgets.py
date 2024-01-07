import pytest
from incident.budgets import Limits, charge


def test_budget_charges_do_not_mutate_input_and_stop_at_bounds():
    used = {"steps": 0, "model_calls": 0, "effects": 0, "seconds": 0.0}
    result = charge(used, Limits(steps=2, models=1, effects=1, seconds=2), "model", 0.5)
    assert result["model_calls"] == 1 and used["steps"] == 0
    with pytest.raises(ValueError, match="budget"):
        charge(result, Limits(models=1), "model", 0.1)
    with pytest.raises(ValueError):
        charge(used, Limits(), "effect", -1)
    with pytest.raises(ValueError, match="budget"):
        charge(used, Limits(seconds=1), "read", 1.1)
