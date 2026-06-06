"""
shaz/core/config.py
Gerenciamento centralizado de configuração.
Carrega settings.json, voice_config.json e variáveis de ambiente (.env).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv


class Config:
    """
    Gerenciador de configuração singleton.
    Carrega e provê acesso a todas as configurações do sistema.
    """

    _instance: Optional["Config"] = None
    _settings: Dict[str, Any] = {}
    _voice_config: Dict[str, Any] = {}
    _base_path: Path

    def __new__(cls, base_path: Optional[Path] = None) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._base_path = base_path or Path(__file__).parent.parent
            cls._instance._load_all()
        return cls._instance

    def _load_all(self) -> None:
        """Carrega todas as fontes de configuração."""
        # Carrega .env
        env_path = self._base_path.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        # Carrega settings.json
        settings_path = self._base_path / "config" / "settings.json"
        if settings_path.exists():
            with open(settings_path, "r", encoding="utf-8") as f:
                self._settings = json.load(f)
        else:
            self._settings = {}

        # Carrega voice_config.json
        voice_path = self._base_path / "config" / "voice_config.json"
        if voice_path.exists():
            with open(voice_path, "r", encoding="utf-8") as f:
                self._voice_config = json.load(f)
        else:
            self._voice_config = {}

    def reload(self) -> None:
        """Recarrega todas as configurações do disco."""
        self._load_all()

    # ─── App Settings ─────────────────────────────────────────────────────

    @property
    def app_name(self) -> str:
        return self._settings.get("app", {}).get("name", "Shaz AI")

    @property
    def app_version(self) -> str:
        return self._settings.get("app", {}).get("version", "1.0.0")

    @property
    def language(self) -> str:
        return self._settings.get("app", {}).get("language", "pt-BR")

    @property
    def theme(self) -> str:
        return self._settings.get("app", {}).get("theme", "dark")

    @property
    def window_width(self) -> int:
        return self._settings.get("app", {}).get("window_width", 1200)

    @property
    def window_height(self) -> int:
        return self._settings.get("app", {}).get("window_height", 800)

    @property
    def start_minimized(self) -> bool:
        return self._settings.get("app", {}).get("start_minimized", False)

    @property
    def auto_start_voice(self) -> bool:
        return self._settings.get("app", {}).get("auto_start_voice", False)

    # ─── LLM Settings ─────────────────────────────────────────────────────

    @property
    def llm_provider(self) -> str:
        return self._settings.get("llm", {}).get("provider", "openai")

    @llm_provider.setter
    def llm_provider(self, value: str) -> None:
        self._settings.setdefault("llm", {})["provider"] = value

    def get_llm_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        prov = provider or self.llm_provider
        return self._settings.get("llm", {}).get(prov, {})

    # ─── Voice Settings ───────────────────────────────────────────────────

    @property
    def stt_engine(self) -> str:
        return self._settings.get("voice", {}).get("stt_engine", "whisper")

    @property
    def stt_model(self) -> str:
        return self._settings.get("voice", {}).get("stt_model", "base")

    @property
    def stt_language(self) -> str:
        return self._settings.get("voice", {}).get("stt_language", "pt")

    @property
    def tts_engine(self) -> str:
        return self._settings.get("voice", {}).get("tts_engine", "edge")

    @property
    def tts_voice(self) -> str:
        return self._settings.get("voice", {}).get("tts_voice", "pt-BR-FranciscaNeural")

    # ─── Voice Config ─────────────────────────────────────────────────────

    @property
    def voice_model(self) -> str:
        return self._voice_config.get("voice_model", "xtts")

    @property
    def voice_speaker(self) -> str:
        return self._voice_config.get("speaker", "shaz")

    @property
    def voice_fallback_chain(self) -> list:
        return self._voice_config.get("fallback_chain", ["xtts", "piper", "edge"])

    def get_xtts_config(self) -> Dict[str, Any]:
        return self._voice_config.get("xtts", {})

    def get_piper_config(self) -> Dict[str, Any]:
        return self._voice_config.get("piper", {})

    def get_edge_config(self) -> Dict[str, Any]:
        return self._voice_config.get("edge", {})

    # ─── Memory Settings ──────────────────────────────────────────────────

    @property
    def memory_engine(self) -> str:
        return self._settings.get("memory", {}).get("engine", "sqlite")

    @property
    def memory_db_path(self) -> str:
        return self._settings.get("memory", {}).get("db_path", "data/memory.db")

    @property
    def max_history_per_conversation(self) -> int:
        return self._settings.get("memory", {}).get("max_history_per_conversation", 100)

    # ─── Audio Settings ───────────────────────────────────────────────────

    @property
    def audio_sample_rate(self) -> int:
        return self._settings.get("audio", {}).get("sample_rate", 16000)

    @property
    def audio_channels(self) -> int:
        return self._settings.get("audio", {}).get("channels", 1)

    @property
    def audio_chunk_size(self) -> int:
        return self._settings.get("audio", {}).get("chunk_size", 1024)

    # ─── Log Settings ─────────────────────────────────────────────────────

    @property
    def log_level(self) -> str:
        return self._settings.get("logs", {}).get("level", "INFO")

    @property
    def log_max_file_size_mb(self) -> int:
        return self._settings.get("logs", {}).get("max_file_size_mb", 10)

    @property
    def log_retention_days(self) -> int:
        return self._settings.get("logs", {}).get("retention_days", 7)

    def is_log_category_enabled(self, category: str) -> bool:
        return self._settings.get("logs", {}).get("categories", {}).get(category, True)

    # ─── API Keys (from .env) ─────────────────────────────────────────────

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", "")

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # ─── Path Helpers ─────────────────────────────────────────────────────

    @property
    def base_path(self) -> Path:
        return self._base_path

    @property
    def data_path(self) -> Path:
        path = self._base_path / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def assets_path(self) -> Path:
        return self._base_path / "assets"

    @property
    def logs_path(self) -> Path:
        path = self._base_path.parent / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get(self, key: str, default: Any = None) -> Any:
        """Acessa configuração aninhada via notação de pontos (ex: 'llm.openai.model')."""
        keys = key.split(".")
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Define um valor de configuração aninhado."""
        keys = key.split(".")
        target = self._settings
        for k in keys[:-1]:
            target = target.setdefault(k, {})
        target[keys[-1]] = value

    def save_settings(self) -> None:
        """Salva as configurações atuais no disco."""
        settings_path = self._base_path / "config" / "settings.json"
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(self._settings, f, indent=2, ensure_ascii=False)

    def save_voice_config(self) -> None:
        """Salva a configuração de voz atual no disco."""
        voice_path = self._base_path / "config" / "voice_config.json"
        with open(voice_path, "w", encoding="utf-8") as f:
            json.dump(self._voice_config, f, indent=2, ensure_ascii=False)