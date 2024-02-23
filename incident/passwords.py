import hashlib
import hmac
import secrets

ITERATIONS = 210000


def hash_password(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 128:
        raise ValueError("Use a password between 12 and 128 characters")
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${value}"


def verify_password(password, encoded):
    try:
        algorithm, count, salt, expected = encoded.split("$")
        if (
            algorithm != "pbkdf2_sha256"
            or int(count) != ITERATIONS
            or len(password) > 128
        ):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(count)
        ).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, AttributeError):
        return False
