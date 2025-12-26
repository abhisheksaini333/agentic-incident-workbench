import pytest
from incident.rate_limit import RateLimit

def test_limiter_invalid_configuration_and_clock_never_mutate_state():
    for values in [dict(limit=0),dict(limit=True),dict(max_keys=-1),dict(max_keys=1.5)]:
        with pytest.raises(ValueError): RateLimit(**values)
    limiter=RateLimit(limit=1,max_keys=2)
    for now in [True,float("nan"),float("inf"),"1"]:
        with pytest.raises(ValueError): limiter.allow("alice",now)
    assert not limiter.entries
    assert limiter.allow("alice",1)
    assert not limiter.allow("alice",2)
    assert limiter.allow("alice",61)
