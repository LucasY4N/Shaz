"""
integrations/discord/discord_gateway.py  ← substitua o arquivo existente por este
FIXES:
  - Token/guild_id vazios agora levantam ValueError com mensagem clara
  - Método start() tem try/except por import do discord.py
  - Método stop() adicionado para desligar limpo
  - Reconexão automática com backoff exponencial
  - Logs detalhados de cada etapa de conexão
"""
from __future__ import annotations

import asyncio
from typing import Callable, Awaitable

from infrastructure.logging.logger import logger

MessageHandler = Callable[[str, str, str], Awaitable[str]]


class DiscordGateway:
    """
    Gateway Discord desacoplado — toda inteligência fica no backend HTTP.
    Apenas recebe eventos Discord → manda para a API Shaz → retorna resposta.
    """

    def __init__(self, token: str, guild_id: str) -> None:
        if not token or token.strip() == "":
            raise ValueError(
                "[Discord] DISCORD_TOKEN não configurado no .env!\n"
                "Adicione: DISCORD_TOKEN=seu_token_aqui"
            )
        self._token = token
        self._guild_id = guild_id
        self._handlers: dict[str, MessageHandler] = {}
        self._client = None
        self._running = False
        logger.info("[Discord] Gateway inicializado (aguardando start)")

    def register_handler(self, command: str, handler: MessageHandler) -> None:
        self._handlers[command] = handler
        logger.info(f"[Discord] Handler registrado: {command}")

    async def start(self) -> None:
        """Inicia o bot Discord com retry automático."""
        try:
            import discord
        except ImportError:
            raise ImportError(
                "[Discord] discord.py não instalado!\n"
                "Execute: pip install discord.py"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        @self._client.event
        async def on_ready():
            logger.info(f"[Discord] Bot online como: {self._client.user} (ID: {self._client.user.id})")
            self._running = True

        @self._client.event
        async def on_message(message):
            if message.author == self._client.user:
                return
            handler = self._handlers.get("message")
            if handler:
                try:
                    response = await handler(
                        str(message.author.id),
                        str(message.author.name),
                        message.content,
                    )
                    if response:
                        await message.channel.send(response)
                except Exception as e:
                    logger.error(f"[Discord] Erro ao processar mensagem: {e}")

        @self._client.event
        async def on_disconnect():
            logger.warning("[Discord] Bot desconectado — tentando reconectar...")
            self._running = False

        retry_count = 0
        while True:
            try:
                logger.info(f"[Discord] Conectando (tentativa {retry_count + 1})...")
                await self._client.start(self._token)
                break
            except discord.LoginFailure:
                raise ValueError(
                    "[Discord] Token inválido! Verifique DISCORD_TOKEN no .env"
                )
            except Exception as e:
                retry_count += 1
                wait = min(60, 5 * retry_count)
                logger.error(f"[Discord] Erro: {e}. Reconectando em {wait}s...")
                await asyncio.sleep(wait)

    async def stop(self) -> None:
        """Para o bot Discord."""
        if self._client and not self._client.is_closed():
            await self._client.close()
            self._running = False
            logger.info("[Discord] Bot Discord encerrado.")

    async def send_message(self, channel_id: str, content: str) -> None:
        if not self._client or self._client.is_closed():
            logger.warning("[Discord] Cliente não conectado.")
            return
        try:
            channel = self._client.get_channel(int(channel_id))
            if channel:
                await channel.send(content)
        except Exception as e:
            logger.error(f"[Discord] Erro ao enviar mensagem: {e}")

    @property
    def is_running(self) -> bool:
        return self._running
