import pytest
from app import pairing

def test_pairing_requires_code_and_explicit_acceptance():
    generated = pairing.create_code()
    request = pairing.request_pairing(generated["code"], "Test Android", "Android")
    assert request["state"] == "pending"
    assert request["client_secret"]
    assert request["client_secret"] not in str(pairing.list_requests())
    with pytest.raises(ValueError):
        pairing.request_pairing(generated["code"], "Replay", "Android")
    assert pairing.authorize_device(request.get("device_token")) is False
    decided = pairing.decide(request["request_id"], True)
    assert decided["state"] == "accepted"
    status = pairing.request_status(request["request_id"], request["client_secret"])
    assert status["state"] == "accepted"
    assert status["device_token"]
    assert pairing.authorize_device(status["device_token"]) is True
    revoked = pairing.revoke_device(request["request_id"])
    assert revoked["state"] == "revoked"
    assert pairing.authorize_device(status["device_token"]) is False

def test_wrong_pairing_secret_is_rejected():
    generated = pairing.create_code()
    request = pairing.request_pairing(generated["code"], "Test phone", "Android")
    with pytest.raises(KeyError):
        pairing.request_status(request["request_id"], "wrong-secret")



def test_new_pair_code_invalidates_previous_code(monkeypatch):
    choices = iter(["2"] * 6 + ["3"] * 6)
    monkeypatch.setattr(pairing.secrets, "choice", lambda _alphabet: next(choices))
    old = pairing.create_code()
    new = pairing.create_code()
    assert old["code"] != new["code"]
    with pytest.raises(ValueError):
        pairing.request_pairing(old["code"], "Old code device", "Android")
    request = pairing.request_pairing(new["code"], "Newest code device", "Android")
    assert request["state"] == "pending"
