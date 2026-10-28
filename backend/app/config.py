from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    asr_model: str = "base"
    asr_device: str = "auto"
    asr_compute_type: str = "int8"
    pairing_ttl_seconds: int = 180
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
