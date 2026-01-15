import pytest
from incident.plans import validate_step, make_plan
from test_approval import fixture

def test_malformed_actions_and_plan_versions_fail_with_validation_errors():
    step=dict(action="restart_service",target="checkout",arguments={})
    for value in [None,[],{**step,"action":[]},{**step,"action":{}}]:
        with pytest.raises(ValueError): validate_step(value,"checkout")
    incident=fixture()
    for version in [True,1.2,"1"]:
        with pytest.raises(ValueError): make_plan(incident,incident["evidence"],[step],"alice",version,"restart")
    assert validate_step(step,"checkout")==step
