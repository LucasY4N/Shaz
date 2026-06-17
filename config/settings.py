"""
config/settings.py
Configurações centralizadas via pydantic-settings + .env
Único ponto de verdade para todas as configs do sistema.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Shaz AI"
    app_version: str = "3.0.0"
    environment: Literal["development", "production", "testing"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Server ───────────────────────────────────────────────────────────
    server_host: str = "127.0.0.1"
    server_port: int = 8765

    # ── LLM Providers ───────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    openrouter_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:latest"

    # ── External APIs ────────────────────────────────────────────────────
    github_token: str = ""
    openweather_api_key: str = ""
    tavily_api_key: str = ""

    # ── Database ─────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "shaz_ai"
    sqlite_path: str = "data/memory.db"

    # ── Voice ────────────────────────────────────────────────────────────
    stt_engine: str = "whisper"
    stt_model: str = "base"
    stt_language: str = "pt"
    tts_engine: str = "edge"
    tts_voice: str = "pt-BR-FranciscaNeural"
    elevenlabs_api_key: str = ""

    # ── Image ────────────────────────────────────────────────────────────
    image_provider: str = "local"
    replicate_api_key: str = ""

    # ── Security ─────────────────────────────────────────────────────────
    secret_key: str = "changeme-in-production"
    allowed_origins: list[str] = Field(default=["*"])

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_github(self) -> bool:
        return bool(self.github_token)

    @property
    def has_weather(self) -> bool:
        return bool(self.openweather_api_key)

    @property
    def has_tavily(self) -> bool:
        return bool(self.tavily_api_key)

    def available_llm_providers(self) -> list[str]:
        providers = []
        if self.has_gemini:
            providers.append("gemini")
        if self.has_groq:
            providers.append("groq")
        if self.openai_api_key:
            providers.append("openai")
        if self.openrouter_api_key:
            providers.append("openrouter")
        providers.append("ollama")
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()
