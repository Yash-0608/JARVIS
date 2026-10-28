from app.intent import tokenize, classify_intent

def test_unicode_tokens_preserve_devanagari():
    tokens = tokenize("Jarvis, WhatsApp वर message पाठव")
    assert "WhatsApp" in tokens
    assert "वर" in tokens
    assert "पाठव" in tokens

def test_message_intent_is_preview_only():
    result = classify_intent("Please send a WhatsApp message")
    assert result["intent"] == "send_message"
    assert result["execution"] == "preview_only"

def test_call_intent_does_not_call():
    result = classify_intent("Jarvis call Rahul")
    assert result["intent"] == "call_contact"
    assert result["execution"] == "preview_only"

def test_unknown_request_is_conversation():
    assert classify_intent("How are you?")["intent"] == "general_conversation"
