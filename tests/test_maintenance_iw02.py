import pytest
from incident.budgets import Limits, charge

def test_limits_and_usage_ledger_reject_invalid_numeric_types():
    for fields in [dict(steps=True),dict(models=1.5),dict(effects=False),dict(seconds=True),dict(seconds="3")]:
        with pytest.raises(ValueError): Limits(**fields)
    valid=dict(steps=0,model_calls=0,effects=0,seconds=0.0)
    for field,value in [("steps",-10),("effects",True),("model_calls",0.5),("seconds",float("nan"))]:
        used={**valid,field:value}
        with pytest.raises(ValueError): charge(used,Limits(),"read",0.5)
    for elapsed in [True,"1",float("inf")]:
        with pytest.raises(ValueError): charge(valid,Limits(),"read",elapsed)
    assert charge(valid,Limits(seconds=1),"read",1)["seconds"]==1
    assert valid["steps"]==0
