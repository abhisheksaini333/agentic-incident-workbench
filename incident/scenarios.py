FAULTS = {
    "memory_pressure": {
        "metric": "memory_percent",
        "value": 96,
        "action": "restart_service",
        "arguments": {},
        "logs": [
            "Process heap keeps growing; allocations cannot be reclaimed.",
            "Resident pages climb after every request; the process cannot allocate another buffer.",
        ],
    },
    "cpu_saturation": {
        "metric": "cpu_percent",
        "value": 99,
        "action": "throttle_requests",
        "arguments": {"percent": 30},
        "logs": [
            "Request concurrency exceeds available CPU; execution is saturated.",
            "Run queue exceeds processor capacity during a burst of requests.",
        ],
    },
    "bad_release": {
        "metric": "release_errors",
        "value": 1,
        "action": "rollback_release",
        "arguments": {"release": "stable"},
        "logs": [
            "Errors began immediately after deploying the candidate release.",
            "The previous build was healthy; every request fails on the newly shipped build.",
        ],
    },
    "dependency_outage": {
        "metric": "dependency_ok",
        "value": 0,
        "action": "restore_dependency",
        "arguments": {"dependency": "catalog"},
        "logs": [
            "The catalog dependency refuses connections; upstream lookup fails.",
            "Catalog requests time out while the application process remains responsive.",
        ],
    },
    "disk_pressure": {
        "metric": "disk_percent",
        "value": 99,
        "action": "rotate_logs",
        "arguments": {"keep_files": 2},
        "logs": [
            "The log volume is full; writes fail with no space left.",
            "Log files consumed the volume and no free blocks remain for writes.",
        ],
    },
    "queue_backlog": {
        "metric": "queue_depth",
        "value": 1200,
        "action": "scale_consumers",
        "arguments": {"replicas": 3},
        "logs": [
            "The consumer queue grows faster than the workers can drain it.",
            "Pending jobs accumulate while the consumer pool runs at its configured limit.",
        ],
    },
}


def healthy_state():
    return {"generation": 1, "faults": [], "variant": 0, "effects": 0}


def observation(state):
    metrics = {
        "cpu_percent": 25,
        "memory_percent": 35,
        "disk_percent": 30,
        "queue_depth": 3,
        "error_rate": 0,
        "latency_ms": 20,
        "dependency_ok": 1,
        "release_errors": 0,
    }
    logs = []
    for name in state["faults"]:
        fault = FAULTS[name]
        metrics[fault["metric"]] = fault["value"]
        logs.append(fault["logs"][state["variant"] % len(fault["logs"])])
    if logs:
        metrics.update(error_rate=0.8, latency_ms=600)
    return {
        "generation": state["generation"],
        "metrics": metrics,
        "logs": logs or ["Service requests complete successfully."],
        "healthy": not state["faults"],
    }
