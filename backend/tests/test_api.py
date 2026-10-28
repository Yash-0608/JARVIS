from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

client = TestClient(app)

def test_health_is_available_without_key():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_protected_intent_endpoint_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "jarvis_api_key", "unit-test-key-for-ci-test-suite-123456")
    denied = client.post("/api/intent/preview", json={"text": "Jarvis call Rahul"})
    assert denied.status_code == 401
    accepted = client.post("/api/intent/preview", json={"text": "Jarvis call Rahul"}, headers={"X-JARVIS-API-Key": "unit-test-key"})
    assert accepted.status_code == 200
    assert accepted.json()["execution"] == "preview_only"


def test_pairing_request_rate_limit():
    payload = {"code": "BAD234", "device_name": "Test Android", "device_platform": "Android"}
    for _ in range(8):
        response = client.post("/api/pairing/request", json=payload)
        assert response.status_code == 400
    limited = client.post("/api/pairing/request", json=payload)
    assert limited.status_code == 429
    assert limited.headers.get("retry-after") == "60"


def test_pairing_status_requires_secret_header(monkeypatch):
    from app import pairing
    generated = pairing.create_code()
    created = pairing.request_pairing(generated["code"], "Android test", "Android")
    pairing.decide(created["request_id"], True)
    without_secret = client.get(f"/api/pairing/status/{created['request_id']}")
    assert without_secret.status_code == 404
    with_secret = client.get(
        f"/api/pairing/status/{created['request_id']}",
        headers={"X-JARVIS-Pair-Secret": created["client_secret"]},
    )
    assert with_secret.status_code == 200
    assert with_secret.json()["state"] == "accepted"
    assert with_secret.json()["device_token"]

 
def test_protected_endpoint_rejects_example_placeholder(monkeypatch):
    placeholder = "replace-with-a-long-random-local-key"
    monkeypatch.setattr(settings, "jarvis_api_key", placeholder)
    response = client.post(
        "/api/intent/preview",
        json={"text": "hello"},
        headers={"X-JARVIS-API-Key": placeholder},
    )
    assert response.status_code == 503
