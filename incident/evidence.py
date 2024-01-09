import hashlib
import json
import math

METRICS = {
    "cpu_percent",
    "memory_percent",
    "disk_percent",
    "queue_depth",
    "error_rate",
    "latency_ms",
    "dependency_ok",
    "release_errors",
}


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def snapshot(payload, version):
    if (
        type(payload.get("generation")) is not int
        or payload["generation"] < 1
        or version < 1
    ):
        raise ValueError("Invalid evidence generation")
    metrics = payload.get("metrics", {})
    logs = payload.get("logs", [])
    if not isinstance(metrics, dict) or not set(metrics).issubset(METRICS):
        raise ValueError("Unknown metric")
    if (
        not isinstance(logs, list)
        or len(logs) > 20
        or any(not isinstance(x, str) or len(x) > 500 for x in logs)
    ):
        raise ValueError("Evidence logs exceed their limit")
    observations = []
    for name, value in sorted(metrics.items()):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Metrics must be finite numbers")
        observations.append(
            {
                "reference": "metric:" + name,
                "kind": "metric",
                "name": name,
                "value": value,
            }
        )
    observations.extend(
        {"reference": f"log:{i + 1}", "kind": "log", "text": text}
        for i, text in enumerate(logs)
    )
    result = {
        "version": version,
        "generation": payload["generation"],
        "healthy": payload.get("healthy") is True,
        "observations": observations,
    }
    result["digest"] = digest(result)
    return result
