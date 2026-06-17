"""
discord_bot/bot/cogs/tools_cog.py
Slash commands das ferramentas externas:
  /clima       — clima atual de uma cidade
  /pesquisar   — pesquisa web via Tavily
  /wiki        — busca no Wikipedia
  /github      — analisa repositório GitHub
  /diagnostico — diagnostica erro de código
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config.constants import (
    CMD_CLIMA, CMD_PESQUISAR, CMD_WIKI, CMD_GITHUB, CMD_DIAGNOSTICO,
)
from discord_bot.utils.helpers import (
    weather_embed, github_embed, diagnostic_embed,
    shaz_embed, error_embed, truncate,
)
from discord_bot.utils.logger import log


class ToolsCog(commands.Cog):

    def __init__(self, bot: commands.Bot, shaz_client) -> None:
        self.bot = bot
        self.shaz = shaz_client

    # ── /clima ────────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_CLIMA, description="Veja o clima atual de qualquer cidade")
    @app_commands.describe(cidade="Nome da cidade (ex: Manaus, São Paulo, Tokyo)")
    async def clima(self, interaction: discord.Interaction, cidade: str) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/clima {cidade!r} por {interaction.user}")

        result = await self.shaz.get_weather(cidade)

        if result.get("status") == "error":
            await interaction.followup.send(embed=error_embed(result.get("message", "Erro desconhecido")))
            return

        await interaction.followup.send(embed=weather_embed(result))

    # ── /pesquisar ────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_PESQUISAR, description="Pesquisa na web com a inteligência da Shaz")
    @app_commands.describe(termo="O que você quer pesquisar")
    async def pesquisar(self, interaction: discord.Interaction, termo: str) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/pesquisar {termo!r} por {interaction.user}")

        result = await self.shaz.search_web(termo, max_results=5)

        if result.get("status") == "error":
            await interaction.followup.send(embed=error_embed(result.get("message", "Erro na pesquisa")))
            return

        data = result.get("data", {})
        answer = data.get("answer", "")
        results = data.get("results", [])

        # Monta embed com resposta direta + fontes
        embed = discord.Embed(
            title=f"🔍 Pesquisa: {termo[:80]}",
            description=truncate(answer, 2000) if answer else "Veja as fontes abaixo:",
            color=0x06B6D4,
        )

        for r in results[:4]:
            embed.add_field(
                name=truncate(r.get("title", "Fonte"), 256),
                value=f"[Link]({r.get('url', '#')})\n{truncate(r.get('snippet', ''), 200)}",
                inline=False,
            )

        embed.set_footer(text="Shaz AI • Tavily Search")
        await interaction.followup.send(embed=embed)

    # ── /wiki ─────────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_WIKI, description="Busca um tópico no Wikipedia")
    @app_commands.describe(topico="O que você quer saber (ex: Buraco negro, Python linguagem)")
    async def wiki(self, interaction: discord.Interaction, topico: str) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/wiki {topico!r} por {interaction.user}")

        result = await self.shaz.search_wikipedia(topico)

        if result.get("status") == "error":
            await interaction.followup.send(embed=error_embed(result.get("message", "Tópico não encontrado")))
            return

        data = result.get("data", {})
        embed = discord.Embed(
            title=f"📖 {data.get('title', topico)}",
            description=truncate(data.get("summary", "Sem resumo disponível"), 2000),
            url=data.get("url", ""),
            color=0xF5F5F5,
        )
        embed.set_footer(text="Shaz AI • Wikipedia")
        await interaction.followup.send(embed=embed)

    # ── /github ───────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_GITHUB, description="Analisa um repositório do GitHub")
    @app_commands.describe(
        dono="Usuário ou organização (ex: microsoft)",
        repositorio="Nome do repo (ex: vscode)",
    )
    async def github(
        self,
        interaction: discord.Interaction,
        dono: str,
        repositorio: str,
    ) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/github {dono}/{repositorio} por {interaction.user}")

        result = await self.shaz.analyze_github(dono, repositorio)

        if result.get("status") == "error":
            await interaction.followup.send(embed=error_embed(result.get("message", "Repositório não encontrado")))
            return

        await interaction.followup.send(embed=github_embed(result))

    # ── /diagnostico ──────────────────────────────────────────────────────

    @app_commands.command(name=CMD_DIAGNOSTICO, description="Diagnostica um erro de código com a Shaz")
    @app_commands.describe(
        erro="Cole a mensagem de erro aqui",
        linguagem="Linguagem de programação (padrão: python)",
    )
    async def diagnostico(
        self,
        interaction: discord.Interaction,
        erro: str,
        linguagem: str = "python",
    ) -> None:
        await interaction.response.defer(thinking=True)
        log.info(f"/diagnostico ({linguagem}) por {interaction.user}: {erro[:40]!r}")

        result = await self.shaz.diagnose_error(erro, language=linguagem)

        if result.get("status") == "error":
            await interaction.followup.send(embed=error_embed(result.get("message", "Erro ao diagnosticar")))
            return

        await interaction.followup.send(embed=diagnostic_embed(result))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ToolsCog(bot, bot.shaz_client))
