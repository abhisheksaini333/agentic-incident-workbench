from api_support import api_fixture
from incident.rate_limit import RateLimit


def test_signin_rate_limit_expires_and_does_not_grow_unbounded():
    limiter = RateLimit(limit=2, max_keys=2)
    assert limiter.allow("a", 0) and limiter.allow("a", 1)
    assert not limiter.allow("a", 2)
    assert limiter.allow("a", 62)
    limiter.allow("b", 62)
    limiter.allow("c", 62)
    assert len(limiter.entries) <= 2


def test_health_readiness_and_security_headers_are_distinct():
    store, auth, c, headers = api_fixture()
    assert c.get("/health").json() == {"status": "ok"}
    response = c.get("/ready")
    assert response.json()["status"] == "ready"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-frame-options"] == "DENY"
