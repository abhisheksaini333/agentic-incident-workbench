from engine_support import engine_case
from incident.model_engine import ModelEngine
from incident.graph import GraphRunner
from incident.model_client import REVISION


class FakeModel:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return {
            "text": "memory_pressure",
            "input_tokens": 50,
            "output_tokens": 3,
            "revision": REVISION,
        }


def test_specialists_checkpoint_independently_and_resume_without_repeating_finished_calls():
    store, flow, _, operator, reviewer, simulator, tools = engine_case()
    item = flow.create(operator, "checkout", "Model diagnosis", 1, mode="graph")
    model = FakeModel()
    engine = ModelEngine(store, tools, model, clock=lambda: 10)
    engine.tick("acme", item["id"])
    first = engine.tick("acme", item["id"])
    assert first["diagnosis_index"] == 1
    assert first["budget"]["model_calls"] == 1
    done = GraphRunner(
        ModelEngine(store, tools, model, clock=lambda: 10)
    ).run_until_pause("acme", item["id"])
    assert done["status"] == "awaiting_approval"
    assert model.calls == 3
    assert len(done["model_results"]) == 3
    assert [x["label"] for x in done["hypotheses"]] == ["memory_pressure"]
    assert sum(x["rejected"] for x in done["model_results"]) == 2
    GraphRunner(ModelEngine(store, tools, model)).run_until_pause("acme", item["id"])
    assert model.calls == 3


def test_single_agent_abstains_when_model_cannot_support_a_diagnosis():
    store, flow, _, operator, _, _, tools = engine_case()

    class Uncertain(FakeModel):
        def generate(self, prompt):
            result = super().generate(prompt)
            result["text"] = "delete_database"
            return result

    item = flow.create(operator, "checkout", "Unknown answer", 1, mode="single")
    result = ModelEngine(store, tools, Uncertain(), clock=lambda: 10).run_until_pause(
        "acme", item["id"]
    )
    assert result["status"] == "escalated"
    assert result["error"] == "insufficient_evidence"
    assert result["budget"]["model_calls"] == 1
    assert result["budget"]["effects"] == 0
