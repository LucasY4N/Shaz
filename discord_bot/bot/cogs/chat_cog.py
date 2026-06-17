"""
discord_bot/bot/cogs/chat_cog.py
Slash command /chat — conversa direta com a Shaz via comando.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config.constants import CMD_CHAT, COLOR_SHAZ
from discord_bot.utils.helpers import shaz_embed, truncate
from discord_bot.utils.logger import log


class ChatCog(commands.Cog):

    def __init__(self, bot: commands.Bot, shaz_client) -> None:
        self.bot = bot
        self.shaz = shaz_client

    @app_commands.command(name=CMD_CHAT, description="Conversa com a Shaz diretamente")
    @app_commands.describe(mensagem="O que você quer perguntar ou dizer para a Shaz")
    async def chat(self, interaction: discord.Interaction, mensagem: str) -> None:
        await interaction.response.defer(thinking=True)

        log.info(f"/chat de {interaction.user}: {mensagem[:60]!r}")
        response = await self.shaz.chat(mensagem)

        embed = shaz_embed(
            title="Resposta da Shaz",
            description=truncate(response),
            color=COLOR_SHAZ,
            footer=f"Perguntou: {interaction.user.display_name}",
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ChatCog(bot, bot.shaz_client))
