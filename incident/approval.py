import uuid
from .evidence import digest
from .identity import require


def valid_binding(incident):
    plan, evidence = incident.get("plan"), incident.get("evidence")
    if not plan or not evidence:
        return False
    fields = {key: value for key, value in plan.items() if key != "digest"}
    return (
        digest(fields) == plan["digest"]
        and plan["incident_id"] == incident["id"]
        and plan["tenant"] == incident["tenant"]
        and plan["evidence_digest"] == evidence["digest"]
        and plan["evidence_version"] == evidence["version"]
        and plan["generation"] == evidence["generation"]
    )


def review(incident, actor, supplied_digest, now):
    require(actor, "approve")
    if not incident.get("plan"):
        raise ValueError("No plan is available for review")
    if (
        actor.tenant != incident["tenant"]
        or actor.subject == incident["plan"]["author"]
    ):
        raise PermissionError("An independent reviewer from this tenant must approve")
    if (
        incident.get("review_request")
        and incident["review_request"]["plan_digest"] == supplied_digest
    ):
        raise ValueError(
            "This plan has a change request; edit it before seeking approval"
        )
    if (
        incident["status"] != "awaiting_approval"
        or not valid_binding(incident)
        or supplied_digest != incident["plan"]["digest"]
    ):
        raise ValueError(
            "The proposed plan or evidence changed; review the current plan"
        )
    return {
        "id": uuid.uuid4().hex,
        "subject": actor.subject,
        "plan_digest": supplied_digest,
        "evidence_digest": incident["evidence"]["digest"],
        "plan_version": incident["plan"]["version"],
        "created_at": now,
        "expires_at": now + 600,
    }


def approved(incident, now):
    approval = incident.get("approval")
    return bool(
        approval
        and valid_binding(incident)
        and approval["expires_at"] > now
        and approval["plan_digest"] == incident["plan"]["digest"]
        and approval["plan_version"] == incident["plan"]["version"]
        and approval["evidence_digest"] == incident["evidence"]["digest"]
    )
