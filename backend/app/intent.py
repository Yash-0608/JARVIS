"""A conservative intent previewer. It never executes actions."""
import unicodedata
import re
from typing import Any

INTENTS: list[tuple[str, tuple[str, ...], str]] = [
    ("send_message", ("send message", "send a message", "whatsapp message", "send whatsapp", "message on whatsapp", "instagram message", "message on instagram", "send dm", "dm to", "message him", "message her", "msg kar", "message kar", "मेसेज", "संदेश पाठव"), "Messaging requires a configured official connector and confirmation."),
    ("social_summary", ("instagram", "social media", "dm", "direct message", "इंस्टाग्राम"), "Social account access depends on supported platform APIs and permissions."),
    ("call_contact", ("call ", "phone him", "phone her", "make a call", "call someone", "फोन कर", "कॉल कर"), "Calling is not enabled in this scaffold; phone permissions and a dedicated Android integration are required."),
    ("set_reminder", ("remind me", "reminder", "याद दिला", "आठवण करून दे"), "Reminder intent detected; scheduler integration is not enabled yet."),
    ("open_app", ("open app", "open chrome", "open vscode", "open vs code", "launch ", "open notepad"), "Windows actions require an explicit allow-listed executor."),
    ("phone_status", ("my phone", "phone status", "missed call", "missed calls", "फोन", "missed call"), "Phone status is available only after the companion app is paired and the relevant permission is granted."),
]

def tokenize(text: str) -> list[str]:
    """Split words/punctuation while retaining Unicode combining marks.

    Python's basic word-character class excludes some combining marks used
    by Indic scripts, so build tokens using Unicode character categories.
    """
    tokens: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    for char in text.strip():
        category = unicodedata.category(char)
        if category[0] in {"L", "N", "M"} or char == "_":
            current.append(char)
        elif char in {"'", "’"} and current:
            current.append(char)
        elif char.isspace():
            flush()
        else:
            flush()
            tokens.append(char)
    flush()
    return tokens

def classify_intent(text: str) -> dict[str, Any]:
    normalized = " ".join(text.casefold().split())
    found = None
    for intent, phrases, note in INTENTS:
        # Match complete terms/phrases, not arbitrary substrings (e.g. "dm" in "admin").
        matched = any(
            re.search(r"(?<!\w)" + re.escape(phrase.casefold().strip()) + r"(?!\w)", normalized, flags=re.UNICODE)
            for phrase in phrases
        )
        if matched:
            found = {"intent": intent, "confidence": 0.72, "note": note}
            break
    if not found:
        found = {"intent": "general_conversation", "confidence": 0.55, "note": "No action will be taken from this preview. Ask a clarifying question if needed."}
    return {"normalized_text": normalized, "tokens": tokenize(text), **found, "execution": "preview_only"}
