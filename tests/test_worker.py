from incident.worker import Worker
from incident.engine import Engine
from engine_support import engine_case


def test_worker_stops_at_a_pending_decision_and_resumes_after_approval():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    worker = Worker(
        s, lambda record: Engine(s, tools, clock=lambda: 10), clock=lambda: 10
    )
    assert worker.once()
    pending = s.get("acme", i["id"])
    assert pending["status"] == "awaiting_approval" and not worker.once()
    f.approve(reviewer, i["id"], pending["plan"]["digest"], pending["revision"], 11)
    restarted = Worker(
        s, lambda record: Engine(s, tools, clock=lambda: 12), clock=lambda: 12
    )
    assert restarted.once()
    final = s.get("acme", i["id"])
    assert final["status"] == "resolved" and len(final["receipts"]) == 1
    assert not restarted.once()
