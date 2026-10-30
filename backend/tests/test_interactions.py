from fastapi.testclient import TestClient

from app import main, ollama, pairing
from app.config import settings

client = TestClient(main.app)
TEST_KEY = "jarvis-interaction-tests-key-1234567890"


def _auth(monkeypatch):
    monkeypatch.setattr(settings, "jarvis_api_key", TEST_KEY)
    return {"X-JARVIS-API-Key": TEST_KEY}


def test_prompt_is_forwarded_to_model_and_answer_is_returned(monkeypatch):
    async def fake_chat(message, model):
        return {"response": f"Echo: {message}", "model": model or "qwen2.5:3b", "done": True}

    monkeypatch.setattr(ollama, "chat", fake_chat)
    response = client.post(
        "/api/ollama/chat",
        json={"message": "Explain Python lists", "model": "qwen2.5:3b"},
        headers=_auth(monkeypatch),
    )
    assert response.status_code == 200
    assert response.json() == {
        "response": "Echo: Explain Python lists",
        "model": "qwen2.5:3b",
        "done": True,
    }


def test_empty_prompt_is_rejected_before_model_call(monkeypatch):
    response = client.post(
        "/api/ollama/chat",
        json={"message": ""},
        headers=_auth(monkeypatch),
    )
    assert response.status_code == 422


def test_model_unavailable_returns_truthful_service_error(monkeypatch):
    async def fail_chat(message, model):
        raise ollama.OllamaError("Ollama is offline")

    monkeypatch.setattr(ollama, "chat", fail_chat)
    response = client.post(
        "/api/ollama/chat",
        json={"message": "Hello Jarvis"},
        headers=_auth(monkeypatch),
    )
    assert response.status_code == 503
    assert "Ollama is offline" in response.json()["detail"]


def test_phone_chat_rejects_unpaired_device(monkeypatch):
    monkeypatch.setattr(pairing, "authorize_device", lambda token: False)
    response = client.post(
        "/api/phone/chat",
        json={"message": "Hello from phone"},
        headers={"X-JARVIS-Device": "invalid-token"},
    )
    assert response.status_code == 401


def test_phone_chat_returns_answer_for_authorized_device(monkeypatch):
    monkeypatch.setattr(pairing, "authorize_device", lambda token: token == "paired-device-token")

    async def fake_chat(message, model):
        return {"response": "Hello from desktop Jarvis", "model": "qwen2.5:3b", "done": True}

    monkeypatch.setattr(ollama, "chat", fake_chat)
    response = client.post(
        "/api/phone/chat",
        json={"message": "Hello Jarvis"},
        headers={"X-JARVIS-Device": "paired-device-token"},
    )
    assert response.status_code == 200
    assert response.json()["response"] == "Hello from desktop Jarvis"


def test_speech_endpoint_rejects_non_audio_upload(monkeypatch):
    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("note.txt", b"not audio", "text/plain")},
        headers=_auth(monkeypatch),
    )
    assert response.status_code == 415


def test_speech_endpoint_returns_transcription_metadata(monkeypatch):
    monkeypatch.setattr(settings, "jarvis_api_key", TEST_KEY)
    monkeypatch.setattr(
        main,
        "_transcribe_path",
        lambda path: {
            "text": "नमस्कार Jarvis",
            "language": "mr",
            "language_probability": 0.97,
            "duration": 1.8,
        },
    )
    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.webm", b"fake-audio-payload", "audio/webm")},
        headers={"X-JARVIS-API-Key": TEST_KEY},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "नमस्कार Jarvis"
    assert response.json()["language"] == "mr"
    assert response.json()["language_probability"] == 0.97


def test_device_revocation_delete_preflight_is_allowed_by_cors():
    response = client.options(
        "/api/pairing/devices/device-123",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "x-jarvis-api-key",
        },
    )
    assert response.status_code == 200
    assert "DELETE" in response.headers.get("access-control-allow-methods", "")
