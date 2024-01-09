import pytest
from incident.plans import make_plan


def test_plan_digest_binds_evidence_arguments_and_version():
    incident = {"id": "incident", "tenant": "acme", "service": "checkout"}
    evidence = {"version": 1, "generation": 2, "digest": "evidence"}
    steps = [
        {
            "action": "scale_consumers",
            "target": "checkout",
            "arguments": {"replicas": 3},
        }
    ]
    plan = make_plan(incident, evidence, steps, "alice", 1, "Increase consumers")
    assert (
        plan["digest"]
        != make_plan(incident, evidence, steps, "alice", 2, "Increase consumers")[
            "digest"
        ]
    )
    steps[0]["arguments"]["replicas"] = 500
    with pytest.raises(ValueError):
        make_plan(incident, evidence, steps, "alice", 1, "Too large")
    with pytest.raises(ValueError):
        make_plan(
            incident,
            evidence,
            [{"action": "shell", "target": "checkout", "arguments": {}}],
            "alice",
            1,
            "Unbounded",
        )
