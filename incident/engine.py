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
            current["evidence_history"].append(evidence)
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

    def _node_diagnose(self, incident):
        reserved = self._reserve(incident, "control")
        started = time.monotonic()
        hypotheses = self.policy.diagnose(incident["evidence"])
        from .diagnosis import supported

        references = {
            item["reference"] for item in incident["evidence"]["observations"]
        }
        for hypothesis in hypotheses:
            if not supported(hypothesis["label"], incident["evidence"]) or not set(
                hypothesis["references"]
            ).issubset(references):
                raise ValueError("Diagnosis is not supported by current evidence")

        def update(current):
            current.update(hypotheses=hypotheses, status="planning", checkpoint="plan")
            append_event(
                current,
                "diagnosis",
                self.policy.name,
                f"Evaluated {len(hypotheses)} supported hypotheses",
                self.clock(),
                [ref for item in hypotheses for ref in item["references"]],
            )

        return self._finish(reserved, started, update)

    def _node_plan(self, incident):
        from .plans import make_plan
        from .scenarios import FAULTS

        reserved = self._reserve(incident, "control")
        started = time.monotonic()

        def update(current):
            if current["evidence"]["healthy"]:
                current.update(status="resolved", checkpoint="complete")
                append_event(
                    current,
                    "no_action",
                    "planner",
                    "Service is healthy; no remediation proposed",
                    self.clock(),
                )
            elif not current["hypotheses"]:
                current.update(
                    status="escalated",
                    checkpoint="complete",
                    error="insufficient_evidence",
                )
                append_event(
                    current,
                    "abstained",
                    "planner",
                    "No supported diagnosis; operator investigation required",
                    self.clock(),
                )
            else:
                steps = [
                    {
                        "action": FAULTS[item["label"]]["action"],
                        "target": current["service"],
                        "arguments": dict(FAULTS[item["label"]]["arguments"]),
                    }
                    for item in current["hypotheses"]
                ]
                current["plan_sequence"] += 1
                rationale = "; ".join(item["reason"] for item in current["hypotheses"])
                current["plan"] = make_plan(
                    current,
                    current["evidence"],
                    steps,
                    current["created_by"],
                    current["plan_sequence"],
                    rationale,
                )
                current.update(
                    status="awaiting_approval", checkpoint="approval", approval=None
                )
                append_event(
                    current,
                    "plan_proposed",
                    "planner",
                    "Exact remediation plan prepared for an independent reviewer",
                    self.clock(),
                )

        return self._finish(reserved, started, update)

    def _node_execute(self, incident):
        reserved = self._reserve(incident, "control")
        started = time.monotonic()
        for entry in self.journal.pending(incident["tenant"], incident["id"]):
            self.journal.reconcile(entry, self.tools, self.clock())
        current = self.store.get(incident["tenant"], incident["id"])
        completed = [
            receipt
            for receipt in current["receipts"]
            if receipt["plan_digest"] == current["plan"]["digest"]
        ]
        index = len(completed)
        if index < len(current["plan"]["steps"]):
            entry = self.journal.prepare(
                current["tenant"], current["id"], current["lease"], index, self.clock()
            )
            self.journal.dispatch(
                entry, current["lease"], self.tools, self.clock(), self.after_effect
            )
        current = self.store.get(incident["tenant"], incident["id"])

        def update(value):
            done = [
                receipt
                for receipt in value["receipts"]
                if receipt["plan_digest"] == value["plan"]["digest"]
            ]
            if len(done) == len(value["plan"]["steps"]):
                value.update(status="verifying", checkpoint="verify")
                append_event(
                    value,
                    "remediation_recorded",
                    "executor",
                    "All reviewed actions have simulator receipts",
                    self.clock(),
                )

        return self._finish(current, started, update)
