"""
discord_bot/bot/events/on_ready.py
Evento on_ready — executado quando o bot conecta ao Discord.
"""
from __future__ import annotations

import discord
from discord.ext import commands

from discord_bot.config.settings import get_discord_settings
from discord_bot.utils.logger import log


class OnReadyCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = get_discord_settings()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        log.info(f"Bot online: {self.bot.user} (ID: {self.bot.user.id})")
        log.info(f"Conectado em {len(self.bot.guilds)} servidor(es)")

        # Status do bot
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=self.settings.discord_status,
            ),
            status=discord.Status.online,
        )

        # Sincroniza slash commands com o servidor configurado
        guild_id = self.settings.guild_id_int
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.bot.tree.copy_global_to(guild=guild)
            synced = await self.bot.tree.sync(guild=guild)
            log.info(f"Slash commands sincronizados: {len(synced)} comandos no servidor {guild_id}")
        else:
            synced = await self.bot.tree.sync()
            log.info(f"Slash commands globais sincronizados: {len(synced)} comandos")

        # Verifica se o backend está online
        if hasattr(self.bot, "shaz_client"):
            online = await self.bot.shaz_client.is_online()
            if online:
                log.info("✅ Backend Shaz AI está ONLINE")
            else:
                log.warning("⚠️ Backend Shaz AI está OFFLINE — respostas podem falhar")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        log.info(f"Bot adicionado ao servidor: {guild.name} (ID: {guild.id})")

    @commands.Cog.listener()
    async def on_disconnect(self) -> None:
        log.warning("Bot desconectado do Discord")

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs) -> None:
        log.error(f"Erro no evento {event}: {args}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnReadyCog(bot))
