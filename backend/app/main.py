from contextlib import asynccontextmanager
from collections import defaultdict, deque
import time
import threading
import os, tempfile
from pathlib import Path
from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
import hmac
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .schemas import ChatRequest, IntentRequest, PairingRequest, PairingDecision, WhatsAppSendRequest, InstagramSendRequest
from . import intent, ollama, pairing, social

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="JARVIS Local Gateway", version="0.1.0", lifespan=lifespan)
_rate_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_asr_init_lock = threading.Lock()

def _transcribe_path(path: str) -> dict:
    # Heavy model loading and inference run off the ASGI event loop.
    from faster_whisper import WhisperModel
    model = getattr(app.state, "asr_model", None)
    if model is None:
        with _asr_init_lock:
            model = getattr(app.state, "asr_model", None)
            if model is None:
                model = WhisperModel(settings.asr_model, device=settings.asr_device, compute_type=settings.asr_compute_type)
                app.state.asr_model = model
    segments, info = model.transcribe(path, beam_size=3, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return {"text": text, "language": info.language, "language_probability": round(float(info.language_probability), 4), "duration": round(float(info.duration), 2)}
# Development-only browser origins. Native Android requests do not use browser CORS.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "X-JARVIS-Device", "X-JARVIS-API-Key", "X-JARVIS-Pair-Secret"])

@app.middleware("http")
async def authenticate_local_api(request: Request, call_next):
    # Pairing bootstrap endpoints use one-time codes/secrets; phone chat uses its per-device token.
    path = request.url.path
    public_bootstrap = path == "/api/health" or path == "/api/pairing/request" or path.startswith("/api/pairing/status/") or path == "/api/phone/chat"
    if request.method != "OPTIONS":
        rate_rule = None
        if path == "/api/pairing/request":
            rate_rule = ("pair-request", 8)
        elif path.startswith("/api/pairing/status/"):
            rate_rule = ("pair-status", 40)
        if rate_rule:
            client_ip = request.client.host if request.client else "unknown"
            key = (client_ip, rate_rule[0])
            now = time.monotonic()
            events = _rate_buckets[key]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= rate_rule[1]:
                return JSONResponse(status_code=429, headers={"Retry-After": "60"}, content={"detail": "Too many pairing attempts. Wait before trying again."})
            events.append(now)
    if request.method == "OPTIONS" or public_bootstrap:
        return await call_next(request)
    expected = settings.jarvis_api_key.strip()
    supplied = request.headers.get("X-JARVIS-API-Key", "")
    if not expected:
        return JSONResponse(status_code=503, content={"detail": "Set JARVIS_API_KEY in backend/.env before using API endpoints."})
    if not supplied or not hmac.compare_digest(supplied, expected):
        return JSONResponse(status_code=401, content={"detail": "Missing or invalid X-JARVIS-API-Key."})
    return await call_next(request)

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
        return await run_in_threadpool(_transcribe_path, tmp_path)
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
def pairing_status(request_id: str, pair_secret: str | None = Header(default=None, alias="X-JARVIS-Pair-Secret")):
    try:
        return pairing.request_status(request_id, pair_secret or "")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

@app.get("/api/pairing/devices")
def pairing_devices():
    return {"devices": pairing.paired_devices()}

@app.delete("/api/pairing/devices/{device_id}")
def revoke_paired_device(device_id: str):
    try:
        return pairing.revoke_device(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@app.post("/api/social/whatsapp/send")
async def social_whatsapp_send(payload: WhatsAppSendRequest):
    try:
        return await social.send_whatsapp(payload.to, payload.text, payload.confirmed)
    except social.SocialAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

@app.post("/api/social/instagram/send")
async def social_instagram_send(payload: InstagramSendRequest):
    try:
        return await social.send_instagram(payload.recipient_id, payload.text, payload.confirmed)
    except social.SocialAPIError as exc:
        raise HTTPException(status_code=409 if "confirmed=true" in str(exc) else 503, detail=str(exc)) from exc

@app.get("/api/integrations")
def integrations():
    wa = social.whatsapp_status()
    ig = social.instagram_status()
    return {"items": [
        {"id": "ollama", "name": "Ollama / Qwen", "state": "configured_by_env", "kind": "local-ai"},
        {"id": "speech", "name": "Speech recognition", "state": "lazy_model_download", "kind": "local-ai"},
        {"id": "android", "name": "Android companion", "state": "pairing_scaffold", "kind": "device"},
        {**wa, "kind": "social"},
        {**ig, "kind": "social"},
        {"id": "telephony", "name": "Calls", "state": "not_implemented", "kind": "phone"},
    ]}
