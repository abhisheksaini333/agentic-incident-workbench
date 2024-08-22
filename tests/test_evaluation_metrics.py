from incident.evaluation import summarize


def test_comparison_denominators_include_escalations_and_healthy_cases():
    base = {
        "mode": "rules",
        "seconds": 1.0,
        "unnecessary_actions": 0,
        "effects": 1,
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    report = summarize(
        [
            {**base, "recovered": True, "status": "resolved"},
            {
                **base,
                "recovered": False,
                "status": "escalated",
                "seconds": 3.0,
                "effects": 0,
            },
        ]
    )
    assert report["rules"]["cases"] == 2
    assert report["rules"]["recovered"] == 1
    assert report["rules"]["median_seconds"] == 2
    assert report["rules"]["p95_seconds"] == 3
