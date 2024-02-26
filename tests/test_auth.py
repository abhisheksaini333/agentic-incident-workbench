import pytest
from incident.store import Store
from incident.auth import AuthManager


def test_existing_signed_session_observes_role_revocation_and_logout():
    s = Store()
    auth = AuthManager(s, "x" * 48)
    auth.create_account("acme", "alice", "a-long-local-password", ["operator"])
    token = auth.login("alice", "a-long-local-password")
    assert auth.actor(token).roles == frozenset({"operator"})
    s.set_roles("acme", "alice", ["viewer"])
    assert auth.actor(token).roles == frozenset({"viewer"})
    auth.logout(token)
    with pytest.raises(PermissionError):
        auth.actor(token)
    with pytest.raises(PermissionError):
        auth.login("alice", "incorrect-password")


def test_invalid_signature_and_empty_current_roles_are_denied():
    s = Store()
    auth = AuthManager(s, "x" * 48)
    auth.create_account("acme", "alice", "a-long-local-password", ["approver"])
    token = auth.login("alice", "a-long-local-password")
    with pytest.raises(PermissionError):
        AuthManager(s, "y" * 48).actor(token)
    s.set_roles("acme", "alice", [])
    with pytest.raises(PermissionError):
        auth.actor(token)
