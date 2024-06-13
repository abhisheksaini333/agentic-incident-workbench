import time
from .engine import Engine
from .model_protocol import GROUPS, build_prompt, parse_diagnosis
from .diagnosis import SIGNALS
from .trace import append_event


class ModelEngine(Engine):
    """Each model call is reserved and completed as its own durable transition."""

    def __init__(self, store, tools, model, **kwargs):
        super().__init__(store, tools, **kwargs)
        self.model = model

    def _node_diagnose(self, incident):
        if incident["evidence"]["healthy"]:
            reserved = self._reserve(incident, "control")
            return self._finish(
                reserved,
                time.monotonic(),
                lambda current: current.update(
                    hypotheses=[], status="planning", checkpoint="plan"
                ),
            )
        groups = (
            GROUPS if incident["mode"] == "graph" else (("generalist", tuple(SIGNALS)),)
        )
        index = incident.get("diagnosis_index", 0)
        if index >= len(groups):
            raise ValueError("Model stage index is outside its bound")
        role, labels = groups[index]
        # Reserve before the network call: a crashed attempt remains in the budget.
        reserved = self._reserve(incident, "model")
        started = time.monotonic()
        prompt = build_prompt(incident["evidence"], labels, role)
        response = self.model.generate(prompt)
        hypotheses, rejected = parse_diagnosis(
            response["text"], labels, incident["evidence"], role
        )

        def update(current):
            current["hypotheses"].extend(hypotheses)
            current["diagnosis_index"] = index + 1
            current["model_results"].append(
                {
                    **response,
                    "role": role,
                    "evidence_version": current["evidence"]["version"],
                    "evidence_digest": current["evidence"]["digest"],
                    "rejected": rejected,
                    "accepted": [item["label"] for item in hypotheses],
                }
            )
            finished = index + 1 == len(groups)
            current.update(
                status="planning" if finished else "diagnosing",
                checkpoint="plan" if finished else "diagnose",
            )
            append_event(
                current,
                "model_diagnosis",
                role,
                f"Accepted {len(hypotheses)} evidence-backed labels; rejected {rejected} outputs",
                self.clock(),
                [ref for item in hypotheses for ref in item["references"]],
            )

        return self._finish(reserved, started, update)
