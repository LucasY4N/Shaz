"""
integrations/discord/discord_gateway.py
Gateway Discord — preparado para integração futura.
O core NUNCA importa este módulo diretamente (arquitetura hexagonal).
"""
from __future__ import annotations
from typing import Callable, Awaitable
from infrastructure.logging.logger import logger


MessageHandler = Callable[[str, str, str], Awaitable[str]]
# (user_id: str, username: str, message: str) -> response: str


class DiscordGateway:
    """
    Gateway de entrada para mensagens Discord.
    Responsabilidade: receber eventos Discord → chamar use cases do core.
    O core nunca sabe que o Discord existe.
    """

    def __init__(self, token: str, guild_id: str) -> None:
        self._token = token
        self._guild_id = guild_id
        self._handlers: dict[str, MessageHandler] = {}
        logger.info("[Discord] Gateway initialized (not yet connected)")

    def register_handler(self, command: str, handler: MessageHandler) -> None:
        """Registra um handler para um comando/evento específico."""
        self._handlers[command] = handler
        logger.debug(f"[Discord] handler registered: {command}")

    async def start(self) -> None:
        """
        Inicia o bot Discord.
        Requer: pip install discord.py
        Implementação completa na Fase 5 do roadmap.
        """
        logger.info("[Discord] Starting bot (Phase 5 — not yet implemented)")
        # TODO: Fase 5
        # import discord
        # intents = discord.Intents.default()
        # intents.message_content = True
        # client = discord.Client(intents=intents)
        #
        # @client.event
        # async def on_message(message):
        #     if message.author == client.user:
        #         return
        #     handler = self._handlers.get("message")
        #     if handler:
        #         response = await handler(str(message.author.id), str(message.author), message.content)
        #         await message.channel.send(response)
        #
        # await client.start(self._token)
        raise NotImplementedError("Discord integration disponível na Fase 5")

    async def send_message(self, channel_id: str, content: str) -> None:
        """Envia mensagem para um canal Discord."""
        logger.debug(f"[Discord] send to {channel_id}: {content[:50]}")
        raise NotImplementedError("Discord integration disponível na Fase 5")
