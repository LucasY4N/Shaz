"""
discord_bot/bot/cogs/status_cog.py
Slash commands de status e ajuda:
  /status — status do sistema Shaz
  /ajuda  — lista todos os comandos disponíveis
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config.constants import CMD_STATUS, CMD_AJUDA, COLOR_SHAZ
from discord_bot.utils.helpers import status_embed, shaz_embed
from discord_bot.utils.logger import log


class StatusCog(commands.Cog):

    def __init__(self, bot: commands.Bot, shaz_client) -> None:
        self.bot = bot
        self.shaz = shaz_client

    @app_commands.command(name=CMD_STATUS, description="Veja o status atual do sistema Shaz AI")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/status por {interaction.user}")

        data = await self.shaz.get_status()
        await interaction.followup.send(embed=status_embed(data))

    @app_commands.command(name=CMD_AJUDA, description="Lista todos os comandos da Shaz")
    async def ajuda(self, interaction: discord.Interaction) -> None:
        embed = shaz_embed(
            title="Comandos disponíveis",
            color=COLOR_SHAZ,
        )

        embed.add_field(
            name="💬 Chat",
            value=(
                "`/chat` — Conversa direto com a Shaz\n"
                "Ou mencione `@Shaz` em qualquer mensagem"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔧 Ferramentas",
            value=(
                "`/clima <cidade>` — Clima atual\n"
                "`/pesquisar <termo>` — Pesquisa na web\n"
                "`/wiki <tópico>` — Busca no Wikipedia\n"
                "`/github <dono> <repo>` — Análise de repositório\n"
                "`/diagnostico <erro>` — Diagnóstico de código"
            ),
            inline=False,
        )
        embed.add_field(
            name="🎤 Voz",
            value=(
                "`/entrar` — Shaz entra no seu canal de voz\n"
                "`/sair` — Shaz sai do canal de voz\n"
                "`/falar <texto>` — Shaz fala algo no canal"
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ Sistema",
            value=(
                "`/status` — Status do sistema\n"
                "`/ajuda` — Esta mensagem"
            ),
            inline=False,
        )
        embed.set_footer(text="Shaz AI • Pyxis-7 • NEXUS v3.0")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatusCog(bot, bot.shaz_client))
