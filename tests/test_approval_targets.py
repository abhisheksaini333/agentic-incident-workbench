import pytest
from incident.approval import review
from incident.identity import Actor


def test_missing_plan_and_foreign_reviewer_fail_closed():
    actor = Actor("acme", "reviewer", frozenset({"approver"}))
    with pytest.raises(ValueError, match="No plan"):
        review({"tenant": "acme", "plan": None}, actor, "digest", 0)
    with pytest.raises(PermissionError):
        review({"tenant": "beta", "plan": {"author": "other"}}, actor, "digest", 0)
