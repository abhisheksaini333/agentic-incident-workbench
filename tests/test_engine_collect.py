from incident.engine import Engine
from engine_support import engine_case


def test_collection_persists_evidence_and_releases_its_worker_lease():
    s, f, i, operator, reviewer, sim, tools = engine_case()
    result = Engine(s, tools, clock=lambda: 1).tick("acme", i["id"])
    assert result["status"] == "diagnosing" and result["checkpoint"] == "diagnose"
    assert result["evidence"]["version"] == 1 and result["evidence"]["generation"] == 2
    assert result["budget"]["steps"] == 1 and result["lease"] is None
