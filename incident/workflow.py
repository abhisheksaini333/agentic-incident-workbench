from .approval import review
from .domain import new_incident
from .identity import require
from .plans import make_plan
from .trace import append_event


class Workflow:
    def __init__(self, store):
        self.store = store

    def create(self, actor, service, title, now, mode="rules"):
        incident = new_incident(actor, service, title, now, mode=mode)
        append_event(incident, "opened", actor.subject, "Incident opened", now)
        return self.store.create(incident)

    def edit(self, actor, key, steps, rationale, revision, now):
        require(actor, "edit")

        def change(incident):
            if incident["status"] not in {"awaiting_approval", "approved"}:
                raise ValueError("This incident is not awaiting a reviewable plan")
            incident["plan_sequence"] = (
                max(incident.get("plan_sequence", 0), incident["plan"]["version"]) + 1
            )
            incident["plan"] = make_plan(
                incident,
                incident["evidence"],
                steps,
                actor.subject,
                incident["plan_sequence"],
                rationale,
            )
            incident["review_request"] = None
            incident["approval"] = None
            incident["lease"] = None
            incident["status"] = "awaiting_approval"
            incident["checkpoint"] = "approval"
            append_event(
                incident,
                "plan_edited",
                actor.subject,
                "Plan edited; prior approval invalidated",
                now,
            )

        return self.store.mutate(actor.tenant, key, change, revision)

    def approve(self, actor, key, plan_digest, revision, now):
        def change(incident):
            incident["approval"] = review(incident, actor, plan_digest, now)
            incident["status"] = "approved"
            incident["checkpoint"] = "execute"
            append_event(
                incident,
                "approved",
                actor.subject,
                "Exact plan and evidence approved",
                now,
            )

        return self.store.mutate(actor.tenant, key, change, revision)

    def cancel(self, actor, key, revision, now):
        require(actor, "edit")

        def change(incident):
            if incident["status"] in {"resolved", "cancelled"}:
                raise ValueError("Incident is already finished")
            incident["status"] = "cancelled"
            incident["lease"] = None
            incident["approval"] = None
            append_event(
                incident,
                "cancelled",
                actor.subject,
                "Further work cancelled; existing receipts are retained",
                now,
            )

        return self.store.mutate(actor.tenant, key, change, revision)

    def retry(self, actor, key, revision, now):
        require(actor, "collect")

        def change(incident):
            if incident["status"] not in {"escalated", "awaiting_approval", "approved"}:
                raise ValueError(
                    "Incident cannot restart evidence collection in this state"
                )
            incident["status"] = "collecting"
            incident["checkpoint"] = "collect"
            incident["lease"] = None
            incident["approval"] = None
            incident["plan"] = None
            incident["hypotheses"] = []
            incident["error"] = None
            append_event(
                incident,
                "recollect",
                actor.subject,
                "New evidence requested; prior plan and approval invalidated",
                now,
            )

        return self.store.mutate(actor.tenant, key, change, revision)

    def resume(self, actor, key, revision, now):
        from .approval import approved

        require(actor, "collect")

        def change(incident):
            if incident["status"] != "escalated" or not approved(incident, now):
                raise ValueError(
                    "Resume requires a stopped incident with an unexpired exact approval"
                )
            incident.update(
                status="approved", checkpoint="execute", lease=None, error=None
            )
            append_event(
                incident,
                "resumed",
                actor.subject,
                "Approved work resumed; pending receipts will be reconciled first",
                now,
            )

        return self.store.mutate(actor.tenant, key, change, revision)

    def request_changes(self, actor, key, revision, reason, now):
        require(actor, "approve")
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
            raise ValueError("Explain the requested changes in 1 to 500 characters")

        def change(incident):
            if (
                incident["status"] not in {"awaiting_approval", "approved"}
                or not incident["plan"]
            ):
                raise ValueError("This plan is no longer awaiting a review decision")
            if incident["plan"]["author"] == actor.subject:
                raise PermissionError("A different reviewer must make this decision")
            incident["review_request"] = {
                "subject": actor.subject,
                "reason": reason.strip(),
                "plan_digest": incident["plan"]["digest"],
            }
            incident.update(
                approval=None,
                lease=None,
                status="awaiting_approval",
                checkpoint="approval",
            )
            append_event(
                incident, "changes_requested", actor.subject, reason.strip(), now
            )

        return self.store.mutate(actor.tenant, key, change, revision)
