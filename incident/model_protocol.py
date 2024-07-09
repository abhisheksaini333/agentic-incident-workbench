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
    # Calibration uses the model's language classification capability. Logs are
    # untrusted observations: generated labels still pass deterministic metric
    # support checks before any plan can exist, and humans approve all effects.
    logs = " ".join(
        item["text"][:180] for item in evidence["observations"] if item["kind"] == "log"
    )[:720]
    return (
        "Classify this incident: "
        + logs
        + " Options: "
        + ", ".join(labels)
        + ", none. Answer:"
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
