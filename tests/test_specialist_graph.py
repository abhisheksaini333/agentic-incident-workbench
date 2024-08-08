from engine_support import engine_case
from incident.graph import GraphRunner
from incident.model_engine import ModelEngine
from incident.model_client import REVISION


def test_each_specialist_is_a_real_graph_node_with_shared_evidence_binding():
    store, flow, _, operator, _, _, tools = engine_case()
    item = flow.create(operator, "checkout", "Graph nodes", 1, mode="graph")

    class Model:
        def generate(self, prompt):
            return {
                "text": "none",
                "input_tokens": 25,
                "output_tokens": 1,
                "revision": REVISION,
            }

    runner = GraphRunner(ModelEngine(store, tools, Model(), clock=lambda: 10))
    assert set(runner.SPECIALISTS).issubset(runner.compiled.nodes)
    done = runner.run_until_pause("acme", item["id"])
    assert [x["role"] for x in done["model_results"]] == list(runner.SPECIALISTS)
    assert {x["evidence_digest"] for x in done["model_results"]} == {
        done["evidence"]["digest"]
    }
    assert done["status"] == "escalated"
