"""
infrastructure/config/settings.py
Configurações centralizadas via pydantic-settings + .env
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "shaz_ai"

    # LLM
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""

    # Discord
    discord_token: str = ""
    discord_guild_id: str = ""

    # Image
    image_provider: str = "local"
    replicate_api_key: str = ""

    # Voice
    stt_engine: str = "google"
    tts_engine: str = "pyttsx3"
    elevenlabs_api_key: str = ""

    # App
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
