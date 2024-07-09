from incident.model_protocol import build_prompt, parse_diagnosis, GROUPS
from incident.evidence import snapshot
from incident.scenarios import observation


def test_untrusted_output_cannot_create_unsupported_or_out_of_role_actions():
    evidence = snapshot(
        observation({"generation": 2, "faults": ["memory_pressure"], "variant": 1}), 1
    )
    labels = GROUPS[0][1]
    result, rejected = parse_diagnosis(
        "memory_pressure, bad_release, delete_database", labels, evidence, "capacity"
    )
    assert [item["label"] for item in result] == ["memory_pressure"]
    assert rejected == 2
    assert result[0]["references"] == ["metric:memory_percent"]
    prompt = build_prompt(evidence, labels, "capacity")
    assert "Resident pages climb" in prompt
    assert len(prompt) < 1200
    assert "delete_database" not in prompt
    assert parse_diagnosis("none", labels, evidence, "capacity") == ([], 0)
