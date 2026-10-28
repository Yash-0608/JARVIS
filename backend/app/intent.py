"""A conservative intent previewer. It never executes actions."""
import re
from typing import Any

TOKEN_RE = re.compile(r"[\w]+(?:['’][\w]+)*|[^\w\s]", re.UNICODE)

INTENTS: list[tuple[str, tuple[str, ...], str]] = [
    ("send_message", ("send message", "whatsapp", "message him", "message her", "send a message", "msg kar", "message kar", "मेसेज", "संदेश पाठव"), "Messaging requires a configured official connector and confirmation."),
    ("social_summary", ("instagram", "social media", "dm", "direct message", "इंस्टाग्राम"), "Social account access depends on supported platform APIs and permissions."),
    ("call_contact", ("call ", "phone him", "phone her", "make a call", "call someone", "फोन कर", "कॉल कर"), "Calling is not enabled in this scaffold; phone permissions and a dedicated Android integration are required."),
    ("set_reminder", ("remind me", "reminder", "याद दिला", "आठवण करून दे"), "Reminder intent detected; scheduler integration is not enabled yet."),
    ("open_app", ("open app", "open chrome", "open vscode", "open vs code", "launch ", "open notepad"), "Windows actions require an explicit allow-listed executor."),
    ("phone_status", ("my phone", "phone status", "missed call", "missed calls", "फोन", "missed call"), "Phone status is available only after the companion app is paired and the relevant permission is granted."),
]

def tokenize(text: str) -> list[str]:
    """Split words/punctuation without destroying Devanagari or other Unicode."""
    return TOKEN_RE.findall(text.strip())

def classify_intent(text: str) -> dict[str, Any]:
    normalized = " ".join(text.casefold().split())
    found = None
    for intent, phrases, note in INTENTS:
        if any(p.casefold() in normalized for p in phrases):
            found = {"intent": intent, "confidence": 0.72, "note": note}
            break
    if not found:
        found = {"intent": "general_conversation", "confidence": 0.55, "note": "No action will be taken from this preview. Ask a clarifying question if needed."}
    return {"normalized_text": normalized, "tokens": tokenize(text), **found, "execution": "preview_only"}
