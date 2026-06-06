"""
shaz/utils/logger.py
Sistema de logs profissional com Rich e logging padrão.
Categorias: INFO, VOICE, STT, TTS, MEMORY, API, SYSTEM, ERROR, DEBUG.
Logs em tempo real com formatação colorida e rotação de arquivos.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, Set

from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text
from rich.theme import Theme

# ─── Tema personalizado para as categorias ───────────────────────────────

CUSTOM_THEME = Theme({
    "log.info": "bold cyan",
    "log.voice": "bold magenta",
    "log.stt": "bold yellow",
    "log.tts": "bold blue",
    "log.memory": "bold green",
    "log.api": "bold white",
    "log.system": "bold bright_black",
    "log.error": "bold red",
    "log.debug": "dim white",
    "log.warning": "bold orange3",
})

CONSOLE = Console(theme=CUSTOM_THEME)

# ─── Categorias de log ──────────────────────────────────────────────────

LOG_CATEGORIES: Dict[str, int] = {
    "INFO": logging.INFO,
    "VOICE": logging.INFO + 1,
    "STT": logging.INFO + 2,
    "TTS": logging.INFO + 3,
    "MEMORY": logging.INFO + 4,
    "API": logging.INFO + 5,
    "SYSTEM": logging.INFO + 6,
    "ERROR": logging.ERROR,
    "DEBUG": logging.DEBUG,
    "WARNING": logging.WARNING,
}

# Registra níveis personalizados
for _name, _level in LOG_CATEGORIES.items():
    if _name not in ["INFO", "ERROR", "DEBUG", "WARNING"]:
        logging.addLevelName(_level, _name)


# ─── Callbacks para logs em tempo real na UI ─────────────────────────────

class LogEmitter:
    """Emite logs para múltiplos listeners (ex: UI dashboard)."""

    _listeners: Set[callable] = set()

    @classmethod
    def add_listener(cls, callback: callable) -> None:
        cls._listeners.add(callback)

    @classmethod
    def remove_listener(cls, callback: callable) -> None:
        cls._listeners.discard(callback)

    @classmethod
    def emit(cls, record: logging.LogRecord) -> None:
        for listener in cls._listeners:
            try:
                listener(record)
            except Exception:
                pass


class EmittingHandler(logging.Handler):
    """Handler que emite logs para os listeners da UI."""

    def emit(self, record: logging.LogRecord) -> None:
        LogEmitter.emit(record)


# ─── Configuração do Logger ──────────────────────────────────────────────

_LOG_CONFIGURED = False


def setup_logger(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    max_file_size_mb: int = 10,
    retention_days: int = 7,
    enabled_categories: Optional[Set[str]] = None,
) -> logging.Logger:
    """
    Configura o sistema de logs completo.

    Args:
        log_level: Nível mínimo de log (INFO, DEBUG, etc.)
        log_dir: Diretório para arquivos de log
        max_file_size_mb: Tamanho máximo por arquivo de log
        retention_days: Dias de retenção de logs
        enabled_categories: Categorias habilitadas (None = todas)

    Returns:
        Instância do logger configurada
    """
    global _LOG_CONFIGURED

    logger = logging.getLogger("ShazAI")
    if _LOG_CONFIGURED:
        return logger

    logger.setLevel(logging.DEBUG)  # Captura tudo, filtra nos handlers

    # ── Remove handlers existentes ──────────────────────────────────────
    logger.handlers.clear()

    # ── Rich Console Handler ────────────────────────────────────────────
    rich_handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        show_time=True,
        show_level=True,
        markup=True,
    )
    rich_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)

    # ── File Handler com rotação ────────────────────────────────────────
    if log_dir is None:
        log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "shaz.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=retention_days,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # ── UI Emitting Handler ─────────────────────────────────────────────
    emitting_handler = EmittingHandler()
    emitting_handler.setLevel(logging.DEBUG)
    logger.addHandler(emitting_handler)

    _LOG_CONFIGURED = True

    logger.info(f"Logger initialized | level={log_level} | file={log_file}")
    return logger


def get_logger() -> logging.Logger:
    """Retorna a instância do logger ShazAI."""
    return logging.getLogger("ShazAI")


# ─── Classe adaptadora para compatibilidade ─────────────────────────────

class LoggerAdapter:
    """
    Adaptador para usar o logger com interface simplificada.
    Usa apenas métodos padrão do logging (info, error, debug, warning)
    para compatibilidade antes do setup_logger() ser chamado.
    """

    def __init__(self) -> None:
        self._logger = get_logger()

    def _log(self, category: str, msg: str) -> None:
        """Log com marcador de categoria usando logging padrão."""
        self._logger.info(f"[{category}] {msg}")

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def voice(self, msg: str) -> None:
        self._log("VOICE", msg)

    def stt(self, msg: str) -> None:
        self._log("STT", msg)

    def tts(self, msg: str) -> None:
        self._log("TTS", msg)

    def memory(self, msg: str) -> None:
        self._log("MEMORY", msg)

    def api(self, msg: str) -> None:
        self._log("API", msg)

    def system(self, msg: str) -> None:
        self._log("SYSTEM", msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)


# ─── Singleton para exportação ──────────────────────────────────────────

logger = LoggerAdapter()

__all__ = [
    "logger",
    "setup_logger",
    "get_logger",
    "LogEmitter",
    "LOG_CATEGORIES",
    "CONSOLE",
]