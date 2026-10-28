"""In-memory development pairing registry.

This is a LAN-development starter, not a production security boundary. Use TLS,
persistent storage, rate limits and revocation before exposing the service.
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
import hmac, secrets, uuid
from .config import settings

@dataclass
class PairRequest:
    request_id: str
    device_name: str
    device_platform: str
    created_at: str
    client_secret: str
    device_token: str
    state: str = "pending"

_codes: dict[str, datetime] = {}
_requests: dict[str, PairRequest] = {}

def _public_request(req: PairRequest) -> dict:
    return {"request_id": req.request_id, "device_name": req.device_name,
            "device_platform": req.device_platform, "created_at": req.created_at,
            "state": req.state}

def create_code() -> dict:
    code = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(6))
    ttl = max(30, min(settings.pairing_ttl_seconds, 600))
    _codes[code] = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    return {"code": code, "expires_in": ttl}

def request_pairing(code: str, device_name: str, platform: str) -> dict:
    code = code.strip().upper()
    expiry = _codes.get(code)
    now = datetime.now(timezone.utc)
    if not expiry or expiry < now:
        _codes.pop(code, None)
        raise ValueError("Pairing code is invalid or expired")
    _codes.pop(code, None)  # one-time code: burn before creating request
    req = PairRequest(
        request_id=uuid.uuid4().hex,
        device_name=device_name.strip(),
        device_platform=platform.strip(),
        created_at=now.isoformat(),
        client_secret=secrets.token_urlsafe(24),
        device_token=secrets.token_urlsafe(32),
    )
    _requests[req.request_id] = req
    # Secret is returned only in the response to the device that submitted the code.
    return {**_public_request(req), "client_secret": req.client_secret}

def list_requests() -> list[dict]:
    return [_public_request(r) for r in _requests.values() if r.state == "pending"]

def decide(request_id: str, accept: bool) -> dict:
    req = _requests.get(request_id)
    if not req:
        raise KeyError("Pairing request was not found")
    if req.state != "pending":
        raise ValueError("Pairing request has already been handled")
    req.state = "accepted" if accept else "rejected"
    return _public_request(req)

def request_status(request_id: str, client_secret: str) -> dict:
    req = _requests.get(request_id)
    if not req or not hmac.compare_digest(req.client_secret, client_secret):
        raise KeyError("Pairing request was not found or the client secret is invalid")
    result = {"request_id": req.request_id, "state": req.state}
    if req.state == "accepted":
        result["device_token"] = req.device_token
    return result

def authorize_device(token: str | None) -> bool:
    if not token:
        return False
    return any(req.state == "accepted" and hmac.compare_digest(req.device_token, token)
               for req in _requests.values())

def paired_devices() -> list[dict]:
    return [{"id": req.request_id, "device_name": req.device_name,
             "device_platform": req.device_platform, "paired_at": req.created_at}
            for req in _requests.values() if req.state == "accepted"]
