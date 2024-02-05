from incident.simulator import Simulator


def test_workload_and_metrics_change_after_recovery():
    s = Simulator()
    s.provision("acme", "checkout")
    before = s.inject("acme", "checkout", ["queue_backlog"])
    assert s.workload("acme", "checkout")["status"] == 503
    assert (
        'incident_demo_queue_depth{tenant="acme",service="checkout"} 1200'
        in s.prometheus("acme", "checkout")
    )
    s.apply(
        "acme",
        "checkout",
        {
            "action": "scale_consumers",
            "target": "checkout",
            "arguments": {"replicas": 3},
        },
        "effect-key-123456",
        before["generation"],
    )
    assert s.workload("acme", "checkout")["status"] == 200
    assert (
        'incident_demo_queue_depth{tenant="acme",service="checkout"} 3'
        in s.prometheus("acme", "checkout")
    )
