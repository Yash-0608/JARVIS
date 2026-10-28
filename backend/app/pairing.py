"""In-memory development pairing registry. Use authenticated TLS and persistent storage before production."""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import secrets, string, uuid
from .config import settings

@dataclass
class PairRequest:
    request_id: str
    device_name: str
    device_platform: str
    created_at: str
    state: str = "pending"

_codes: dict[str, datetime] = {}
_requests: dict[str, PairRequest] = {}
_paired: dict[str, dict] = {}

def create_code() -> dict:
    # Avoid ambiguous glyphs and expire quickly; server is for trusted-LAN development only.
    code = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6))
    expiry = datetime.now(timezone.utc) + timedelta(seconds=max(30, min(settings.pairing_ttl_seconds, 600)))
    _codes[code] = expiry
    return {"code": code, "expires_in": int((expiry - datetime.now(timezone.utc)).total_seconds())}

def request_pairing(code: str, device_name: str, platform: str) -> dict:
    code = code.strip().upper()
    expiry = _codes.get(code)
    now = datetime.now(timezone.utc)
    if not expiry or expiry < now:
        _codes.pop(code, None)
        raise ValueError("Pairing code is invalid or expired")
    # One request per code, then burn it to prevent replay.
    _codes.pop(code, None)
    req = PairRequest(uuid.uuid4().hex, device_name.strip(), platform.strip(), now.isoformat())
    _requests[req.request_id] = req
    return asdict(req)

def list_requests() -> list[dict]:
    return [asdict(r) for r in _requests.values() if r.state == "pending"]

def decide(request_id: str, accept: bool) -> dict:
    req = _requests.get(request_id)
    if not req:
        raise KeyError("Pairing request was not found")
    req.state = "accepted" if accept else "rejected"
    if accept:
        _paired[req.request_id] = {"device_name": req.device_name, "device_platform": req.device_platform, "paired_at": datetime.now(timezone.utc).isoformat()}
    return asdict(req)

def request_status(request_id: str) -> dict:
    req = _requests.get(request_id)
    if not req:
        raise KeyError("Pairing request was not found")
    return {"request_id": req.request_id, "state": req.state}

def paired_devices() -> list[dict]:
    return [{"id": key, **value} for key, value in _paired.items()]
