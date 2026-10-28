import asyncio
import pytest
from app import social
from app.config import settings

def test_social_sends_require_explicit_confirmation():
    with pytest.raises(social.SocialAPIError) as err:
        asyncio.run(social.send_whatsapp("+919876543210", "hello", confirmed=False))
    assert err.value.status_code == 409

def test_whatsapp_unconfigured_is_not_sent(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_cloud_api_token", "")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "")
    with pytest.raises(social.SocialAPIError) as err:
        asyncio.run(social.send_whatsapp("+919876543210", "hello", confirmed=True))
    assert err.value.status_code == 503

def test_invalid_whatsapp_recipient_is_validation_error(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_cloud_api_token", "test-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "test-id")
    with pytest.raises(social.SocialAPIError) as err:
        asyncio.run(social.send_whatsapp("not-a-number", "hello", confirmed=True))
    assert err.value.status_code == 422

def test_instagram_recipient_must_be_scoped_numeric_id(monkeypatch):
    monkeypatch.setattr(settings, "instagram_graph_api_token", "test-token")
    monkeypatch.setattr(settings, "instagram_business_account_id", "1234567")
    with pytest.raises(social.SocialAPIError) as err:
        asyncio.run(social.send_instagram("@someusername", "hello", confirmed=True))
    assert err.value.status_code == 422
