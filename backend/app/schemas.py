from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    model: str | None = None

class IntentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

class PairingCreateResponse(BaseModel):
    code: str
    expires_in: int

class PairingRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)
    device_name: str = Field(min_length=1, max_length=80)
    device_platform: str = Field(default="Android", max_length=40)

class PairingDecision(BaseModel):
    request_id: str = Field(min_length=6, max_length=100)
    accept: bool


class WhatsAppSendRequest(BaseModel):
    to: str = Field(min_length=7, max_length=30)
    text: str = Field(min_length=1, max_length=4096)
    confirmed: bool = False

class InstagramSendRequest(BaseModel):
    recipient_id: str = Field(min_length=5, max_length=30)
    text: str = Field(min_length=1, max_length=1000)
    confirmed: bool = False
