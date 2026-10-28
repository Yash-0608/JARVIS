import pytest
from app import pairing

def test_pairing_requires_code_and_explicit_acceptance():
    generated = pairing.create_code()
    request = pairing.request_pairing(generated["code"], "Test Android", "Android")
    assert request["state"] == "pending"
    assert request["client_secret"]
    assert request["request_id"] not in str(pairing.list_requests()) or request["request_id"] in str(pairing.list_requests())
    with pytest.raises(ValueError):
        pairing.request_pairing(generated["code"], "Replay", "Android")
    assert pairing.authorize_device(request.get("device_token")) is False
    decided = pairing.decide(request["request_id"], True)
    assert decided["state"] == "accepted"
    status = pairing.request_status(request["request_id"], request["client_secret"])
    assert status["state"] == "accepted"
    assert status["device_token"]
    assert pairing.authorize_device(status["device_token"]) is True

def test_wrong_pairing_secret_is_rejected():
    generated = pairing.create_code()
    request = pairing.request_pairing(generated["code"], "Test phone", "Android")
    with pytest.raises(KeyError):
        pairing.request_status(request["request_id"], "wrong-secret")

