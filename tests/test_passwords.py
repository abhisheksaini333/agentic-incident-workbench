from incident.passwords import hash_password, verify_password
import pytest


def test_password_hashes_are_unique_and_wrong_passwords_fail():
    password = "a-long-local-password"
    one = hash_password(password)
    two = hash_password(password)
    assert one != two and password not in one
    assert verify_password(password, one) and not verify_password("wrong-password", one)
    assert not verify_password(password, "malformed")
    with pytest.raises(ValueError):
        hash_password("short")
