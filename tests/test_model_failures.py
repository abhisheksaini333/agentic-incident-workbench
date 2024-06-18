from engine_support import engine_case
from incident.model_engine import ModelEngine
from incident.budgets import Limits
from incident.model_client import REVISION


def test_failed_model_call_is_charged_and_cannot_silently_fall_back_to_rules():
    store, flow, _, operator, _, _, tools = engine_case()

    class Broken:
        def generate(self, prompt):
            raise TimeoutError("model unavailable")

    item = flow.create(operator, "checkout", "Unavailable model", 1, mode="single")
    result = ModelEngine(store, tools, Broken(), clock=lambda: 10).run_until_pause(
        "acme", item["id"]
    )
    assert result["status"] == "escalated"
    assert result["budget"]["model_calls"] == 1
    assert result["plan"] is None


def test_graph_stops_before_a_model_call_that_would_exceed_its_budget():
    store, flow, _, operator, _, _, tools = engine_case()

    class Counted:
        calls = 0

        def generate(self, prompt):
            self.calls += 1
            return {
                "text": "none",
                "input_tokens": 12,
                "output_tokens": 1,
                "revision": REVISION,
            }

    model = Counted()
    item = flow.create(operator, "checkout", "Bounded model", 1, mode="graph")
    result = ModelEngine(
        store, tools, model, limits=Limits(models=1), clock=lambda: 10
    ).run_until_pause("acme", item["id"])
    assert result["status"] == "escalated"
    assert model.calls == 1
    assert result["budget"]["model_calls"] == 1
