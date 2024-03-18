SIGNALS = {
    "memory_pressure": ("memory_percent", lambda value: value >= 90),
    "cpu_saturation": ("cpu_percent", lambda value: value >= 90),
    "bad_release": ("release_errors", lambda value: value > 0),
    "dependency_outage": ("dependency_ok", lambda value: value == 0),
    "disk_pressure": ("disk_percent", lambda value: value >= 95),
    "queue_backlog": ("queue_depth", lambda value: value >= 100),
}


def supported(label, evidence):
    if label not in SIGNALS:
        return False
    metric, predicate = SIGNALS[label]
    values = {
        item["name"]: item["value"]
        for item in evidence["observations"]
        if item["kind"] == "metric"
    }
    return metric in values and predicate(values[metric])


class RulesPolicy:
    name = "rules"
    model_calls = 0

    def diagnose(self, evidence):
        return [
            {
                "label": label,
                "references": ["metric:" + spec[0]],
                "source": "rules",
                "reason": f"The {spec[0]} signal crosses its runbook threshold",
            }
            for label, spec in SIGNALS.items()
            if supported(label, evidence)
        ]
