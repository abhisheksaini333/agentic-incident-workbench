import httpx
import pytest
from incident.model_client import ModelClient,REVISION

def test_model_response_envelope_is_object_and_bounded():
    valid=dict(text="memory_pressure",revision=REVISION,input_tokens=3,output_tokens=2)
    for payload in [None,[],{**valid,"ignored":"x"*17000}]:
        client=ModelClient("http://model.local","k"*24,httpx.MockTransport(lambda r:httpx.Response(200,json=payload)))
        try:
            with pytest.raises(ValueError): client.generate("diagnose")
        finally: client.close()
