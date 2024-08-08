from typing import TypedDict
from langgraph.graph import StateGraph, END


class Cursor(TypedDict):
    tenant: str
    incident_id: str
    stage: str
    paused: bool


class GraphRunner:
    """Original 0.0.21 graph API; durable state lives in the incident store.

    Each graph node commits one fenced domain transition. Human review returns
    from invoke; a new invocation reads the stored cursor after approval.
    No in-memory checkpointer or background continuation authorizes effects.
    """

    STAGES = ("collect", "diagnose", "plan", "execute", "verify")
    SPECIALISTS = ("capacity", "change_and_dependency", "storage_and_queue")
    PAUSED = {"awaiting_approval", "resolved", "escalated", "cancelled"}

    def __init__(self, engine):
        self.engine = engine
        graph = StateGraph(Cursor)
        graph.add_node("route", self._route)
        graph.set_entry_point("route")
        for stage in (*self.STAGES, *self.SPECIALISTS):
            expected = "diagnose" if stage in self.SPECIALISTS else stage
            graph.add_node(stage, self._node(expected))
            graph.add_edge(stage, "route")
        graph.add_conditional_edges(
            "route",
            self._next,
            {
                **{stage: stage for stage in (*self.STAGES, *self.SPECIALISTS)},
                "stop": END,
            },
        )
        self.compiled = graph.compile()

    def _route(self, state):
        item = self.engine.store.get(state["tenant"], state["incident_id"])
        stage = item["checkpoint"]
        if stage == "diagnose" and item.get("mode") == "graph":
            index = item.get("diagnosis_index", 0)
            if not 0 <= index < len(self.SPECIALISTS):
                raise ValueError("Invalid specialist checkpoint")
            stage = self.SPECIALISTS[index]
        return {"stage": stage, "paused": item["status"] in self.PAUSED}

    def _next(self, state):
        if state["paused"]:
            return "stop"
        if state["stage"] not in (*self.STAGES, *self.SPECIALISTS):
            raise ValueError("Unknown persisted graph stage")
        return state["stage"]

    def _node(self, stage):
        def execute(state):
            item = self.engine.tick(
                state["tenant"], state["incident_id"], expected=stage
            )
            return {
                "stage": item["checkpoint"],
                "paused": item["status"] in self.PAUSED,
            }

        return execute

    def run_until_pause(self, tenant, key):
        # Reconcile factual receipts even when cancellation has paused effects.
        self.engine.reconcile(tenant, key)
        self.compiled.invoke(
            {"tenant": tenant, "incident_id": key, "stage": "collect", "paused": False},
            config={"recursion_limit": 2 * self.engine.limits.steps + 8},
        )
        return self.engine.store.get(tenant, key)
