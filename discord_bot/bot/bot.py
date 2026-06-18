"""
discord_bot/bot/bot.py
Classe principal do bot Discord da Shaz.
Responsabilidade única: montar o bot, carregar cogs e gerenciar o lifecycle.
"""
from __future__ import annotations

import discord
from discord.ext import commands

from discord_bot.bot.voice.voice_manager import VoiceManager
from discord_bot.config.settings import get_discord_settings
from discord_bot.utils.logger import log
from discord_bot.utils.shaz_client import ShazClient


class ShazBot(commands.Bot):
    """
    Bot Discord da Shaz AI.
    Herda de commands.Bot e adiciona:
      - shaz_client: conexão com o backend
      - voice_manager: gerenciamento de voz
    """

    def __init__(self) -> None:
        self.settings = get_discord_settings()

        intents = discord.Intents.default()
        intents.message_content = True   # necessário para ler conteúdo das mensagens
        intents.voice_states = True      # necessário para voz
        intents.members = True           # necessário para display_name

        super().__init__(
            command_prefix=self.settings.discord_prefix,
            intents=intents,
            help_command=None,           # desabilita o !help padrão (usamos slash)
        )

        # Dependências injetadas no bot (acessíveis pelos cogs)
        self.shaz_client = ShazClient(
            base_url=self.settings.shaz_api_url,
            timeout=self.settings.shaz_api_timeout,
        )
        self.voice_manager = VoiceManager(self, self.shaz_client)

    async def setup_hook(self) -> None:
        """Chamado automaticamente pelo discord.py antes do bot conectar."""
        log.info("Carregando extensões (cogs)...")
        await self._load_extensions()
        log.info("Todas as extensões carregadas")

    async def _load_extensions(self) -> None:
        """Carrega todos os cogs e eventos."""
        extensions = [
            # Eventos
            "discord_bot.bot.events.on_ready",
            "discord_bot.bot.events.on_message",
            # Comandos
            "discord_bot.bot.cogs.chat_cog",
            "discord_bot.bot.cogs.tools_cog",
            "discord_bot.bot.cogs.voice_cog",
            "discord_bot.bot.cogs.status_cog",
            "discord_bot.bot.cogs.video_cog",
        ]

        for ext in extensions:
            try:
                await self.load_extension(ext)
                log.info(f"  ✅ {ext}")
            except Exception as e:
                log.error(f"  ❌ {ext}: {e}")

    async def close(self) -> None:
        """Cleanup ao desligar o bot."""
        log.info("Desligando ShazBot...")

        # Sai de todos os canais de voz
        for guild_id in list(self.voice_manager._voice_clients.keys()):
            await self.voice_manager.leave(guild_id)

        # Fecha o cliente HTTP
        await self.shaz_client.close()

        await super().close()
        log.info("ShazBot desligado com sucesso")
