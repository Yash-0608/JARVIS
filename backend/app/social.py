"""Explicit-confirmation Meta messaging adapter.

Credentials stay server-side. Only official Cloud/Graph API endpoints are used.
"""
import re
from typing import Any
import httpx
from .config import settings

class SocialAPIError(RuntimeError):
    pass

def whatsapp_status() -> dict[str, Any]:
    ready = bool(settings.whatsapp_cloud_api_token and settings.whatsapp_phone_number_id)
    return {"id": "whatsapp", "name": "WhatsApp Cloud API", "state": "credentials_ready" if ready else "needs_credentials", "configured": ready}

def instagram_status() -> dict[str, Any]:
    ready = bool(settings.instagram_graph_api_token and settings.instagram_business_account_id)
    return {"id": "instagram", "name": "Instagram Messaging API", "state": "credentials_ready" if ready else "needs_credentials", "configured": ready}

def _graph_url(path: str) -> str:
    version = settings.meta_graph_version.strip().strip("/")
    base = settings.meta_graph_base_url.rstrip("/")
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise SocialAPIError("META_GRAPH_VERSION must look like v26.0")
    return f"{base}/{version}/{path.lstrip('/')}"

async def send_whatsapp(to: str, text: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise SocialAPIError("Message not sent. Set confirmed=true only after reviewing and approving the exact recipient and message.")
    status = whatsapp_status()
    if not status["configured"]:
        raise SocialAPIError("WhatsApp Cloud API needs WHATSAPP_CLOUD_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID in backend/.env.")
    recipient = re.sub(r"\D", "", to)
    if not re.fullmatch(r"\d{7,15}", recipient):
        raise SocialAPIError("Recipient must be an international phone number with 7 to 15 digits.")
    if not text.strip() or len(text) > 4096:
        raise SocialAPIError("Message must contain 1 to 4096 characters.")
    url = _graph_url(f"{settings.whatsapp_phone_number_id}/messages")
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient,
               "type": "text", "text": {"preview_url": False, "body": text.strip()}}
    return await _post_meta(url, settings.whatsapp_cloud_api_token, payload, "WhatsApp")

async def send_instagram(recipient_id: str, text: str, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise SocialAPIError("Message not sent. Set confirmed=true only after reviewing and approving the exact recipient and message.")
    status = instagram_status()
    if not status["configured"]:
        raise SocialAPIError("Instagram Messaging API needs INSTAGRAM_GRAPH_API_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID in backend/.env.")
    # Instagram-scoped recipient ID, not a username or phone number.
    if not re.fullmatch(r"\d{5,30}", recipient_id.strip()):
        raise SocialAPIError("Use the Instagram-scoped recipient ID received through a supported messaging conversation.")
    if not text.strip() or len(text) > 1000:
        raise SocialAPIError("Instagram message must contain 1 to 1000 characters.")
    url = _graph_url(f"{settings.instagram_business_account_id}/messages")
    payload = {"recipient": {"id": recipient_id.strip()}, "message": {"text": text.strip()}}
    return await _post_meta(url, settings.instagram_graph_api_token, payload, "Instagram")

async def _post_meta(url: str, token: str, payload: dict[str, Any], provider: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        if response.is_error:
            # Avoid returning raw request headers/tokens; only report safe provider message fields.
            try:
                body = response.json()
                error = body.get("error", {})
                detail = error.get("message") or error.get("type") or "Provider rejected the request"
            except ValueError:
                detail = "Provider rejected the request"
            raise SocialAPIError(f"{provider} API returned HTTP {response.status_code}: {detail}")
        data = response.json()
        return {"provider": provider, "submitted": True, "message_id": data.get("messages", [{}])[0].get("id") if data.get("messages") else data.get("message_id"), "provider_response": data}
    except httpx.HTTPError as exc:
        raise SocialAPIError(f"{provider} API request failed: {type(exc).__name__}") from exc
