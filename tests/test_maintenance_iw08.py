import pytest
from pydantic import ValidationError
from incident.api import LoginRequest,IncidentRequest,RevisionRequest,RolesRequest,SimulationRequest

def test_requests_reject_unknown_fields_and_coerced_revisions():
    for model,fields in [(LoginRequest,dict(subject="a",password="p")),(IncidentRequest,dict(service="checkout",title="failure")),(RevisionRequest,dict(revision=1)),(RolesRequest,dict(roles=[])),(SimulationRequest,dict(service="checkout",faults=[]))]:
        with pytest.raises(ValidationError): model(**fields,typo=True)
    for value in [True,1.5,"1"]:
        with pytest.raises(ValidationError): RevisionRequest(revision=value)
        with pytest.raises(ValidationError): SimulationRequest(service="checkout",faults=[],variant=value)
