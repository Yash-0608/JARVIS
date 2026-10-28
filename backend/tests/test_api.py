from fastapi.testclient import TestClient
from app.config import settings
from app.main import app

client = TestClient(app)

def test_health_is_available_without_key():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_protected_intent_endpoint_requires_key(monkeypatch):
    monkeypatch.setattr(settings, "jarvis_api_key", "unit-test-key")
    denied = client.post("/api/intent/preview", json={"text": "Jarvis call Rahul"})
    assert denied.status_code == 401
    accepted = client.post("/api/intent/preview", json={"text": "Jarvis call Rahul"}, headers={"X-JARVIS-API-Key": "unit-test-key"})
    assert accepted.status_code == 200
    assert accepted.json()["execution"] == "preview_only"
