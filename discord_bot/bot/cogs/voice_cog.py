"""
discord_bot/bot/cogs/voice_cog.py
Slash commands de voz:
  /entrar — Shaz entra no canal de voz do usuário
  /sair   — Shaz sai do canal de voz
  /falar  — Shaz fala um texto no canal de voz
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.bot.voice.voice_manager import VoiceManager
from discord_bot.config.constants import CMD_VOZ_ENTRAR, CMD_VOZ_SAIR, CMD_VOZ_FALAR
from discord_bot.utils.helpers import success_embed, error_embed, shaz_embed
from discord_bot.utils.logger import log


class VoiceCog(commands.Cog):

    def __init__(self, bot: commands.Bot, voice_manager: VoiceManager) -> None:
        self.bot = bot
        self.voice = voice_manager

    # ── /entrar ───────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_VOZ_ENTRAR, description="Shaz entra no seu canal de voz")
    async def entrar(self, interaction: discord.Interaction) -> None:
        # Verifica se o usuário está em um canal de voz
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                embed=error_embed("Você precisa estar em um canal de voz primeiro!"),
                ephemeral=True,
            )
            return

        channel = interaction.user.voice.channel
        await interaction.response.defer(thinking=True)

        try:
            await self.voice.join(channel)
            embed = success_embed(
                title=f"Entrei em #{channel.name}",
                description="Pode usar `/falar <texto>` para eu falar algo, ou `/sair` para me dispensar.",
            )
            await interaction.followup.send(embed=embed)

            # Diz oi ao entrar
            await self.voice.speak(
                interaction.guild_id,
                f"Oi, {interaction.user.display_name}! Estou aqui. O que você precisa?",
            )
            log.info(f"{interaction.user} chamou a Shaz para #{channel.name}")

        except Exception as e:
            log.error(f"/entrar error: {e}")
            await interaction.followup.send(
                embed=error_embed(f"Não consegui entrar no canal: {e}"),
            )

    # ── /sair ─────────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_VOZ_SAIR, description="Shaz sai do canal de voz")
    async def sair(self, interaction: discord.Interaction) -> None:
        if not self.voice.is_connected(interaction.guild_id):
            await interaction.response.send_message(
                embed=error_embed("Não estou em nenhum canal de voz!"),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        # Diz tchau antes de sair
        await self.voice.speak(interaction.guild_id, "Tá bom, até mais!")
        await self.voice.leave(interaction.guild_id)

        await interaction.followup.send(
            embed=success_embed("Saí do canal de voz", "Até mais! 👋"),
        )
        log.info(f"{interaction.user} dispensou a Shaz do canal de voz")

    # ── /falar ────────────────────────────────────────────────────────────

    @app_commands.command(name=CMD_VOZ_FALAR, description="Faz a Shaz falar algo no canal de voz")
    @app_commands.describe(texto="O que a Shaz deve falar")
    async def falar(self, interaction: discord.Interaction, texto: str) -> None:
        if not self.voice.is_connected(interaction.guild_id):
            await interaction.response.send_message(
                embed=error_embed("Não estou em nenhum canal de voz! Use `/entrar` primeiro."),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        success = await self.voice.speak(interaction.guild_id, texto)

        if success:
            embed = shaz_embed(
                title="Falando no canal de voz",
                description=f'"{texto}"',
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=error_embed("Não consegui reproduzir o áudio. Verifique se o FFmpeg está instalado."),
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot, bot.voice_manager))
