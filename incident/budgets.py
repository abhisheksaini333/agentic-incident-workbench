from dataclasses import dataclass
from copy import deepcopy
import math


@dataclass(frozen=True)
class Limits:
    steps: int = 24
    models: int = 6
    effects: int = 3
    seconds: float = 120.0

    def __post_init__(self):
        if not (
            type(self.steps) is int
            and type(self.models) is int
            and type(self.effects) is int
            and type(self.seconds) in (int, float)
            and 1 <= self.steps <= 48
            and 0 <= self.models <= 9
            and 0 <= self.effects <= 3
            and math.isfinite(self.seconds)
            and 1 <= self.seconds <= 180
        ):
            raise ValueError("Invalid execution limits")


def charge(used, limits, kind, elapsed):
    if (
        not isinstance(kind, str)
        or kind not in {"read", "model", "effect", "control"}
        or type(elapsed) not in (int, float)
        or not math.isfinite(elapsed)
        or elapsed < 0
    ):
        raise ValueError("Invalid budget charge")
    if (
        not isinstance(used, dict)
        or any(type(used.get(key)) is not int or used[key] < 0 for key in ("steps", "model_calls", "effects"))
        or type(used.get("seconds")) not in (int, float)
        or not math.isfinite(used["seconds"])
        or used["seconds"] < 0
    ):
        raise ValueError("Invalid budget ledger")
    result = deepcopy(used)
    result["steps"] += 1
    result["seconds"] += elapsed
    result["model_calls"] += kind == "model"
    result["effects"] += kind == "effect"
    if (
        result["steps"] > limits.steps
        or result["seconds"] > limits.seconds
        or result["model_calls"] > limits.models
        or result["effects"] > limits.effects
    ):
        raise ValueError("Execution budget exhausted")
    return result
