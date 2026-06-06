"""
infrastructure/logging/logger.py
Logger centralizado para todo o projeto Shaz AI.
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str | None = "logs/shaz.log") -> None:
    """Configura o logger global com saída colorida e arquivo rotativo."""
    logger.remove()  # Remove handler padrão

    # Console — colorido
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
    )

    # Arquivo rotativo
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
        )


# Exporta o logger já configurado como singleton
__all__ = ["logger", "setup_logger"]
