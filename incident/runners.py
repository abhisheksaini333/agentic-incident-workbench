from .engine import Engine
from .model_engine import ModelEngine
from .graph import GraphRunner


class UnavailableModel:
    def generate(self, prompt):
        raise RuntimeError("Configure the isolated model worker before model diagnosis")


def runner_for(store, tools, incident, model=None, **kwargs):
    mode = incident.get("mode", "rules")
    if mode == "rules":
        return Engine(store, tools, **kwargs)
    if mode not in {"single", "graph"}:
        raise ValueError("Unsupported diagnosis mode")
    engine = ModelEngine(store, tools, model or UnavailableModel(), **kwargs)
    return GraphRunner(engine) if mode == "graph" else engine
