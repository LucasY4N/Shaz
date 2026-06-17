"""
discord_bot/config/settings.py
Configurações exclusivas do bot Discord da Shaz.
Lê do .env da raiz do projeto — sem duplicar chaves.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DiscordSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Discord ───────────────────────────────────────────────────────────
    discord_token: str = ""
    discord_guild_id: str = ""          # ID do servidor (guild) principal
    discord_channel_id: str = ""        # Canal onde a Shaz responde tudo
    discord_prefix: str = "!"           # Prefixo de comandos legados
    discord_status: str = "Observando a tela do usuário 👁"

    # ── Comportamento ─────────────────────────────────────────────────────
    respond_to_mentions: bool = True     # Responde quando mencionada (@Shaz)
    respond_in_channel: bool = True      # Responde no canal configurado
    respond_to_everyone: bool = False    # Responde qualquer msg no servidor
    max_response_length: int = 1900      # Limite do Discord: 2000 chars

    # ── Voz ──────────────────────────────────────────────────────────────
    voice_enabled: bool = True
    voice_auto_leave_seconds: int = 300  # Sai do canal após 5min sem uso

    # ── Shaz Brain (conexão com o backend) ───────────────────────────────
    shaz_api_url: str = "http://localhost:8765"
    shaz_api_timeout: float = 30.0

    # ── LLM (caso rode standalone sem o backend) ──────────────────────────
    gemini_api_key: str = ""
    groq_api_key: str = ""

    @property
    def has_token(self) -> bool:
        return bool(self.discord_token)

    @property
    def guild_id_int(self) -> Optional[int]:
        try:
            return int(self.discord_guild_id) if self.discord_guild_id else None
        except ValueError:
            return None

    @property
    def channel_id_int(self) -> Optional[int]:
        try:
            return int(self.discord_channel_id) if self.discord_channel_id else None
        except ValueError:
            return None


@lru_cache
def get_discord_settings() -> DiscordSettings:
    return DiscordSettings()
