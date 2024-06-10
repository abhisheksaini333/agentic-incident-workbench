import json
import re
from .diagnosis import SIGNALS, supported

GROUPS = (
    ("capacity", ("memory_pressure", "cpu_saturation")),
    ("change_and_dependency", ("bad_release", "dependency_outage")),
    ("storage_and_queue", ("disk_pressure", "queue_backlog")),
)
THRESHOLDS = {
    "memory_pressure": "memory_percent >= 90",
    "cpu_saturation": "cpu_percent >= 90",
    "bad_release": "release_errors > 0",
    "dependency_outage": "dependency_ok == 0",
    "disk_pressure": "disk_percent >= 95",
    "queue_backlog": "queue_depth >= 100",
}


def build_prompt(evidence, labels, role):
    metrics = {SIGNALS[label][0] for label in labels}
    observations = [
        item
        for item in evidence["observations"]
        if item["kind"] == "metric" and item["name"] in metrics
    ]
    # Logs remain visible to people, but untrusted log instructions are excluded
    # from the bounded metric-classification prompt.
    return (
        "Classify an incident from measured evidence. You are the "
        + role
        + " reviewer. "
        "Return only matching labels separated by commas, or none. Do not invent labels.\n"
        + "Rules: "
        + "; ".join(label + " if " + THRESHOLDS[label] for label in labels)
        + "\nEvidence with reference identifiers: "
        + json.dumps(observations, sort_keys=True)
        + "\nMatching labels:"
    )


def parse_diagnosis(text, labels, evidence, role):
    if not isinstance(text, str) or len(text) > 2000:
        raise ValueError("Invalid model response")
    normalized = text.strip().lower().strip(". ")
    if normalized in {"none", "no issues", "healthy"}:
        return [], 0
    pieces = [
        item.strip().strip(".'\"")
        for item in re.split(r"[,;\n]+", normalized)
        if item.strip()
    ]
    results, rejected, seen = [], 0, set()
    for label in pieces:
        if label not in labels or not supported(label, evidence):
            rejected += 1
            continue
        if label in seen:
            continue
        seen.add(label)
        metric = SIGNALS[label][0]
        results.append(
            {
                "label": label,
                "references": ["metric:" + metric],
                "source": "model:" + role,
                "reason": "Model proposed "
                + label
                + "; the "
                + metric
                + " runbook threshold was independently verified",
            }
        )
    return results, rejected
