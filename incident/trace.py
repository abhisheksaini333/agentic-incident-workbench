import uuid


def append_event(incident, kind, actor, message, now, references=None):
    references = references or []
    if (
        not 1 <= len(message) <= 1000
        or len(references) > 30
        or any(len(x) > 100 for x in references)
    ):
        raise ValueError("Trace event exceeds its limit")
    if len(incident["trace"]) >= 500:
        raise ValueError("Incident trace limit reached; archive before further work")
    incident["trace"].append(
        {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "actor": actor,
            "message": message,
            "time": now,
            "references": list(references),
        }
    )
