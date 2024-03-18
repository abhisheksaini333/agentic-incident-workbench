import time
import uuid
from .budgets import Limits, charge
from .evidence import snapshot
from .trace import append_event
from .effects import EffectJournal
from .diagnosis import RulesPolicy


class Engine:
    def __init__(
        self, store, tools, policy=None, limits=None, clock=None, after_effect=None
    ):
        self.store = store
        self.tools = tools
        self.policy = policy or RulesPolicy()
        self.limits = limits or Limits()
        self.clock = clock or time.time
        self.owner = uuid.uuid4().hex
        self.journal = EffectJournal(store, self.limits)
        self.after_effect = after_effect

    def _reserve(self, incident, kind):
        now = self.clock()

        def update(current):
            current["budget"] = charge(current["budget"], self.limits, kind, 0)
            current["lease"]["expires_at"] = now + 60
            if current["status"] == "new":
                current["status"] = "collecting"

        return self.store.worker_update(
            incident["tenant"],
            incident["id"],
            incident["lease"],
            now,
            update,
            incident["revision"],
        )

    def _finish(self, reserved, started, change):
        elapsed = time.monotonic() - started
        now = self.clock()

        def update(current):
            current["budget"]["seconds"] += elapsed
            if current["budget"]["seconds"] > self.limits.seconds:
                current.update(
                    status="escalated",
                    checkpoint="complete",
                    error="active_time_budget",
                )
                append_event(
                    current,
                    "budget_exhausted",
                    "coordinator",
                    "Active execution time budget exhausted",
                    now,
                )
            else:
                change(current)
            current["lease"] = None

        return self.store.worker_update(
            reserved["tenant"],
            reserved["id"],
            reserved["lease"],
            now,
            update,
            reserved["revision"],
        )

    def tick(self, tenant, key, expected=None):
        current = self.store.get(tenant, key)
        if current["status"] in {
            "awaiting_approval",
            "resolved",
            "escalated",
            "cancelled",
        }:
            return current
        if expected and current["checkpoint"] != expected:
            return current
        claimed = self.store.claim(tenant, key, self.owner, self.clock())
        try:
            method = getattr(self, "_node_" + claimed["checkpoint"])
            return method(claimed)
        except Exception as error:

            def fail(incident):
                incident.update(
                    status="escalated",
                    checkpoint="complete",
                    lease=None,
                    error=type(error).__name__,
                )
                append_event(
                    incident,
                    "failed",
                    "coordinator",
                    "Execution stopped safely: " + type(error).__name__,
                    self.clock(),
                )

            try:
                return self.store.worker_update(
                    tenant, key, claimed["lease"], self.clock(), fail
                )
            except ValueError:
                return self.store.get(tenant, key)

    def _node_collect(self, incident):
        reserved = self._reserve(incident, "read")
        started = time.monotonic()
        observed = self.tools.observe(incident["tenant"], incident["service"])
        version = (incident["evidence"]["version"] if incident["evidence"] else 0) + 1
        evidence = snapshot(observed, version)

        def update(current):
            current.update(
                evidence=evidence,
                hypotheses=[],
                plan=None,
                approval=None,
                status="diagnosing",
                checkpoint="diagnose",
            )
            append_event(
                current,
                "evidence",
                "collector",
                "Service snapshot collected",
                self.clock(),
                [item["reference"] for item in evidence["observations"]],
            )

        return self._finish(reserved, started, update)
