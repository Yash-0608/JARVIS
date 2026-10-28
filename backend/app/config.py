from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    jarvis_api_key: str = ""
    meta_graph_base_url: str = "https://graph.facebook.com"
    meta_graph_version: str = "v26.0"
    whatsapp_cloud_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    instagram_graph_api_token: str = ""
    instagram_business_account_id: str = ""
    asr_model: str = "base"
    asr_device: str = "auto"
    asr_compute_type: str = "int8"
    pairing_ttl_seconds: int = 180
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
