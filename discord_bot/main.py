"""
discord_bot/main.py
Ponto de entrada do bot Discord da Shaz.

Uso:
    python -m discord_bot.main
    OU
    python discord_bot/main.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Garante que a raiz do projeto está no path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from discord_bot.bot.bot import ShazBot
from discord_bot.config.settings import get_discord_settings
from discord_bot.utils.logger import log


async def main() -> None:
    settings = get_discord_settings()

    if not settings.has_token:
        log.error("DISCORD_TOKEN não encontrado no .env!")
        log.error("Adicione: DISCORD_TOKEN=seu_token_aqui")
        sys.exit(1)

    log.info("=" * 50)
    log.info("   Shaz AI — Discord Bot — NEXUS v3.0")
    log.info("=" * 50)
    log.info(f"Backend: {settings.shaz_api_url}")
    log.info(f"Guild ID: {settings.discord_guild_id or 'global'}")
    log.info(f"Canal: {settings.discord_channel_id or 'não configurado'}")
    log.info(f"Voz: {'habilitada' if settings.voice_enabled else 'desabilitada'}")
    log.info("=" * 50)

    bot = ShazBot()

    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        log.info("Interrompido pelo usuário (Ctrl+C)")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
