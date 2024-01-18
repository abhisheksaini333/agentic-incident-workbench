from .approval import review
from .domain import new_incident
from .identity import require
from .plans import make_plan
from .trace import append_event


class Workflow:
    def __init__(self, store):
        self.store = store

    def create(self, actor, service, title, now):
        incident = new_incident(actor, service, title, now)
        append_event(incident, "opened", actor.subject, "Incident opened", now)
        return self.store.create(incident)

    def edit(self, actor, key, steps, rationale, revision, now):
        require(actor, "edit")

        def change(incident):
            if incident["status"] not in {"awaiting_approval", "approved"}:
                raise ValueError("This incident is not awaiting a reviewable plan")
            incident["plan"] = make_plan(
                incident,
                incident["evidence"],
                steps,
                actor.subject,
                incident["plan"]["version"] + 1,
                rationale,
            )
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
