import pytest
from incident.identity import Actor, require


def test_roles_deny_viewer_actions_and_unknown_permissions():
    viewer = Actor("acme", "alice", frozenset({"viewer"}))
    require(viewer, "read")
    with pytest.raises(PermissionError):
        require(viewer, "collect")
    with pytest.raises(PermissionError):
        require(Actor("acme", "bob", frozenset({"operator"})), "approve")
    require(Actor("acme", "carol", frozenset({"approver"})), "approve")
    with pytest.raises(ValueError):
        Actor("../outside", "alice", frozenset({"admin"}))
