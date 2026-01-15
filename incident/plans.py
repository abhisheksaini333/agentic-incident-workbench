from copy import deepcopy
from .evidence import digest

ACTIONS = {
    "restart_service": {},
    "throttle_requests": {"percent": (int, 10, 50)},
    "rollback_release": {"release": (str, {"stable"})},
    "restore_dependency": {"dependency": (str, {"catalog"})},
    "rotate_logs": {"keep_files": (int, 1, 10)},
    "scale_consumers": {"replicas": (int, 2, 4)},
}


def validate_step(step, service):
    if not isinstance(step, dict) or set(step) != {"action", "target", "arguments"} or step["target"] != service:
        raise ValueError("Action target does not match this incident")
    if not isinstance(step["action"], str):
        raise ValueError("Unknown action or arguments")
    schema = ACTIONS.get(step["action"])
    arguments = step["arguments"]
    if (
        schema is None
        or not isinstance(arguments, dict)
        or set(arguments) != set(schema)
    ):
        raise ValueError("Unknown action or arguments")
    for name, rule in schema.items():
        value = arguments[name]
        if (
            type(value) is not rule[0]
            or (rule[0] is int and not rule[1] <= value <= rule[2])
            or (rule[0] is str and value not in rule[1])
        ):
            raise ValueError("Action argument is outside its allowed range")
    return deepcopy(step)


def make_plan(incident, evidence, steps, author, version, rationale):
    if not isinstance(steps, list) or not 1 <= len(steps) <= 3 or type(version) is not int or version < 1:
        raise ValueError("A remediation plan requires one to three bounded actions")
    if not isinstance(rationale, str) or not 1 <= len(rationale.strip()) <= 1000:
        raise ValueError("Explain the proposed remediation")
    checked = [validate_step(step, incident["service"]) for step in steps]
    if len({step["action"] for step in checked}) != len(checked):
        raise ValueError("Do not repeat an action within a plan")
    plan = {
        "incident_id": incident["id"],
        "tenant": incident["tenant"],
        "version": version,
        "evidence_version": evidence["version"],
        "evidence_digest": evidence["digest"],
        "generation": evidence["generation"],
        "steps": checked,
        "author": author,
        "rationale": rationale.strip(),
    }
    plan["digest"] = digest(plan)
    return plan
