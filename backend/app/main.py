from contextlib import asynccontextmanager
import os, tempfile
from pathlib import Path
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .schemas import ChatRequest, IntentRequest, PairingRequest, PairingDecision
from . import intent, ollama, pairing

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="JARVIS Local Gateway", version="0.1.0", lifespan=lifespan)
# Development-only browser origins. Native Android requests do not use browser CORS.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "X-JARVIS-Device"])

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "jarvis-gateway", "version": app.version}

@app.get("/api/ollama/status")
async def ollama_status():
    return await ollama.status()

@app.get("/api/ollama/models")
async def ollama_models():
    try:
        return await ollama.models()
    except ollama.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/api/ollama/chat")
async def ollama_chat(payload: ChatRequest):
    try:
        return await ollama.chat(payload.message, payload.model)
    except ollama.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/api/phone/chat")
async def phone_chat(payload: ChatRequest, device_token: str | None = Header(default=None, alias="X-JARVIS-Device")):
    if not pairing.authorize_device(device_token):
        raise HTTPException(status_code=401, detail="Phone is not paired or access has been revoked. Pair again from the desktop.")
    try:
        return await ollama.chat(payload.message, payload.model)
    except ollama.OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

@app.post("/api/intent/preview")
def intent_preview(payload: IntentRequest):
    return intent.classify_intent(payload.text)

@app.post("/api/speech/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not audio.content_type or not (audio.content_type.startswith("audio/") or audio.content_type in {"application/octet-stream", "video/webm"}):
        raise HTTPException(status_code=415, detail="Upload an audio recording")
    suffix = Path(audio.filename or "recording.webm").suffix[:10] or ".webm"
    tmp_path = None
    try:
        data = await audio.read(20 * 1024 * 1024 + 1)
        if not data or len(data) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio must be between 1 byte and 20 MB")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        from faster_whisper import WhisperModel
        model = getattr(app.state, "asr_model", None)
        if model is None:
            model = WhisperModel(settings.asr_model, device=settings.asr_device, compute_type=settings.asr_compute_type)
            app.state.asr_model = model
        segments, info = model.transcribe(tmp_path, beam_size=3, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return {"text": text, "language": info.language, "language_probability": round(float(info.language_probability), 4), "duration": round(float(info.duration), 2)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Speech recognition failed: {type(exc).__name__}: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

@app.post("/api/pairing/code")
def create_pairing_code():
    return pairing.create_code()

@app.post("/api/pairing/request")
def request_pairing(payload: PairingRequest):
    try:
        return pairing.request_pairing(payload.code, payload.device_name, payload.device_platform)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/api/pairing/requests")
def pairing_requests():
    return {"requests": pairing.list_requests()}

@app.post("/api/pairing/decision")
def pairing_decision(payload: PairingDecision):
    try:
        return pairing.decide(payload.request_id, payload.accept)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.get("/api/pairing/status/{request_id}")
def pairing_status(request_id: str, secret: str):
    try:
        return pairing.request_status(request_id, secret)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/api/pairing/devices")
def pairing_devices():
    return {"devices": pairing.paired_devices()}

@app.get("/api/integrations")
def integrations():
    return {"items": [
        {"id": "ollama", "name": "Ollama / Qwen", "state": "configured_by_env", "kind": "local-ai"},
        {"id": "speech", "name": "Speech recognition", "state": "lazy_model_download", "kind": "local-ai"},
        {"id": "android", "name": "Android companion", "state": "pairing_scaffold", "kind": "device"},
        {"id": "whatsapp", "name": "WhatsApp", "state": "not_configured", "kind": "social"},
        {"id": "instagram", "name": "Instagram", "state": "not_configured", "kind": "social"},
        {"id": "telephony", "name": "Calls", "state": "not_implemented", "kind": "phone"},
    ]}
