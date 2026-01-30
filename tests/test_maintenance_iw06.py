import copy
import pytest
from incident.approval import valid_binding,approved,review
from incident.identity import Actor
from test_approval import fixture

def test_corrupt_approval_records_fail_closed_and_time_is_finite():
    base=fixture(); actor=Actor("acme","bob",frozenset({"approver"}))
    base["approval"]=review(base,actor,base["plan"]["digest"],10)
    assert approved(base,11)
    for field in ["plan","evidence"]:
        for bad in [[1],{"digest":"x"}]:
            value=copy.deepcopy(base);value[field]=bad
            assert not valid_binding(value)
            assert not approved(value,11)
    for bad in [[1],{"expires_at":20},{**base["approval"],"expires_at":float("inf")}]:
        assert not approved({**base,"approval":bad},11)
    for now in [float("nan"),float("inf"),True]:
        assert not approved(base,now)
        with pytest.raises(ValueError): review(base,actor,base["plan"]["digest"],now)
