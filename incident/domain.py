from copy import deepcopy
import uuid
from .identity import identifier, require

TERMINAL = frozenset({"resolved", "escalated", "cancelled"})
TRANSITIONS = {
    "new": {"collecting", "cancelled"},
    "collecting": {"diagnosing", "escalated", "cancelled"},
    "diagnosing": {"planning", "escalated", "cancelled"},
    "planning": {"awaiting_approval", "resolved", "escalated", "cancelled"},
    "awaiting_approval": {"approved", "collecting", "cancelled", "escalated"},
    "approved": {"executing", "collecting", "cancelled", "escalated"},
    "executing": {"verifying", "escalated", "cancelled"},
    "verifying": {"resolved", "escalated", "cancelled"},
    "escalated": {"collecting"},
    "resolved": set(),
    "cancelled": set(),
}


def new_incident(actor, service, title, now):
    require(actor, "collect")
    identifier(service)
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= 160:
        raise ValueError("Enter an incident title of 1 to 160 characters")
    return {
        "id": uuid.uuid4().hex,
        "tenant": actor.tenant,
        "service": service,
        "title": title.strip(),
        "created_by": actor.subject,
        "created_at": now,
        "status": "new",
        "revision": 1,
        "evidence": None,
        "hypotheses": [],
        "plan_sequence": 0,
        "plan": None,
        "approval": None,
        "trace": [],
        "receipts": [],
        "checkpoint": "collect",
        "lease": None,
        "error": None,
        "budget": {"steps": 0, "model_calls": 0, "effects": 0, "seconds": 0.0},
    }


def transition(incident, target):
    if target not in TRANSITIONS.get(incident["status"], set()):
        raise ValueError("Invalid incident state transition")
    result = deepcopy(incident)
    result["status"] = target
    return result
