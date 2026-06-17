"""
discord_bot/bot/events/on_message.py
Evento on_message — trata menções (@Shaz) e mensagens no canal configurado.
Responsabilidade única: detectar quando a Shaz deve responder e delegar ao ShazClient.
"""
from __future__ import annotations

import discord
from discord.ext import commands

from discord_bot.config.constants import EMOJI_THINKING, MAX_MSG_LENGTH
from discord_bot.config.settings import get_discord_settings
from discord_bot.utils.helpers import truncate
from discord_bot.utils.logger import log


class OnMessageCog(commands.Cog):
    """Cog que escuta mensagens e decide se a Shaz deve responder."""

    def __init__(self, bot: commands.Bot, shaz_client) -> None:
        self.bot = bot
        self.shaz = shaz_client
        self.settings = get_discord_settings()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignora mensagens do próprio bot
        if message.author.bot:
            return

        # Ignora mensagens de DM (sem guild)
        if not message.guild:
            return

        should_respond = self._should_respond(message)
        if not should_respond:
            return

        # Limpa o texto removendo a menção se tiver
        content = self._clean_content(message)
        if not content:
            content = "Oi! O que você precisa?"

        log.info(f"Respondendo para {message.author} em #{message.channel}: {content[:60]!r}")

        async with message.channel.typing():
            response = await self.shaz.chat(content)

        # Divide resposta se for muito longa
        for chunk in self._split_response(response):
            await message.reply(chunk, mention_author=False)

    def _should_respond(self, message: discord.Message) -> bool:
        """Define se a Shaz deve responder a esta mensagem."""
        # Menção direta ao bot
        if self.settings.respond_to_mentions and self.bot.user in message.mentions:
            return True

        # Canal específico configurado
        if (
            self.settings.respond_in_channel
            and self.settings.channel_id_int
            and message.channel.id == self.settings.channel_id_int
        ):
            return True

        # Responde a todos (modo servidor inteiro)
        if self.settings.respond_to_everyone:
            return True

        return False

    def _clean_content(self, message: discord.Message) -> str:
        """Remove a menção do bot do início da mensagem."""
        content = message.content
        if self.bot.user:
            content = content.replace(f"<@{self.bot.user.id}>", "").strip()
            content = content.replace(f"<@!{self.bot.user.id}>", "").strip()
        return content.strip()

    def _split_response(self, text: str, limit: int = MAX_MSG_LENGTH) -> list[str]:
        """Divide resposta longa em chunks respeitando o limite do Discord."""
        if len(text) <= limit:
            return [text]

        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            # Tenta cortar no último parágrafo ou ponto
            cut = text.rfind("\n", 0, limit)
            if cut == -1:
                cut = text.rfind(". ", 0, limit)
            if cut == -1:
                cut = limit
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()
        return chunks


async def setup(bot: commands.Bot) -> None:
    """Registrado automaticamente pelo discord.py extension loader."""
    # shaz_client é injetado via bot.shaz_client
    await bot.add_cog(OnMessageCog(bot, bot.shaz_client))
