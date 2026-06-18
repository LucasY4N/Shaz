"""
discord_bot/bot/cogs/video_cog.py
Slash command /video — baixa vídeos de redes sociais.
Suporta: YouTube, TikTok, Instagram, Twitter/X.
"""
from __future__ import annotations

import re
import tempfile
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.config.constants import EMOJI_SUCCESS, EMOJI_ERROR, MAX_MSG_LENGTH
from discord_bot.utils.helpers import success_embed, error_embed
from discord_bot.utils.logger import log


# Padrões de URL para cada plataforma
URL_PATTERNS = {
    "youtube": [
        r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([\w-]{11})",
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([\w-]{11})",
    ],
    "tiktok": [
        r"(?:https?:\/\/)?(?:www\.)?tiktok\.com\/@[\w.-]+\/video\/(\d+)",
        r"(?:https?:\/\/)?vm\.tiktok\.com\/[\w]+",
    ],
    "instagram": [
        r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel|tv)\/([\w-]+)",
        r"(?:https?:\/\/)?(?:www\.)?instagram\.com\/stories\/[\w.-]+\/(\d+)",
    ],
    "twitter": [
        r"(?:https?:\/\/)?(?:www\.)?(?:twitter|x)\.com\/\w+\/status\/(\d+)",
    ],
}


class VideoCog(commands.Cog):
    """
    Cog para download de vídeos de redes sociais.
    Usa yt-dlp internamente (deve estar instalado).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ytdlp_available = self._check_ytdlp()

    def _check_ytdlp(self) -> bool:
        """Verifica se yt-dlp está instalado."""
        try:
            import yt_dlp
            return True
        except ImportError:
            return False

    def _detect_platform(self, url: str) -> Optional[str]:
        """Detecta qual plataforma a URL pertence."""
        for platform, patterns in URL_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, url):
                    return platform
        return None

    @app_commands.command(
        name="video",
        description="Baixa um vídeo do YouTube, TikTok, Instagram ou Twitter/X",
    )
    @app_commands.describe(
        url="Link do vídeo para baixar",
        formato="Formato: mp4 (vídeo) ou mp3 (áudio apenas)",
    )
    @app_commands.choices(formato=[
        app_commands.Choice(name="🎬 MP4 (Vídeo)", value="mp4"),
        app_commands.Choice(name="🎵 MP3 (Áudio)", value="mp3"),
    ])
    async def video(
        self,
        interaction: discord.Interaction,
        url: str,
        formato: app_commands.Choice[str] = "mp4",
    ) -> None:
        if not self._ytdlp_available:
            await interaction.response.send_message(
                embed=error_embed(
                    "yt-dlp não está instalado no servidor.\n"
                    "Peça para o administrador instalar com: `pip install yt-dlp`"
                ),
                ephemeral=True,
            )
            return

        platform = self._detect_platform(url)
        if not platform:
            await interaction.response.send_message(
                embed=error_embed(
                    "⚠ URL não reconhecida!\n\n"
                    "Formatos suportados:\n"
                    "• YouTube: `https://youtube.com/watch?v=...`\n"
                    "• TikTok: `https://tiktok.com/@user/video/...`\n"
                    "• Instagram: `https://instagram.com/p/...`\n"
                    "• Twitter/X: `https://x.com/user/status/...`"
                ),
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)
        log.info(f"/video {platform} por {interaction.user}: {url[:60]}")

        try:
            from yt_dlp import YoutubeDL

            formato_ext = formato.value if isinstance(formato, app_commands.Choice) else formato
            is_audio = formato_ext == "mp3"

            # Configura o yt-dlp
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": tempfile.gettempdir() + "/shaz_video_%(id)s.%(ext)s",
                "noplaylist": True,
            }

            if is_audio:
                ydl_opts.update({
                    "format": "bestaudio/best",
                    "postprocessors": [{
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }],
                })
            else:
                ydl_opts.update({
                    "format": "best[height<=1080]/best",
                    "merge_output_format": "mp4",
                })

            with YoutubeDL(ydl_opts) as ydl:
                # Extrai info e baixa
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if is_audio:
                    filename = filename.rsplit(".", 1)[0] + ".mp3"
                else:
                    filename = filename  # já tem extensão .mp4

                if not os.path.exists(filename):
                    # Tenta achar o arquivo com extensão alternativa
                    base = filename.rsplit(".", 1)[0]
                    for ext in [".mp4", ".mp3", ".webm", ".mkv"]:
                        test = base + ext
                        if os.path.exists(test):
                            filename = test
                            break

                title = info.get("title", "video")
                uploader = info.get("uploader", info.get("channel", "desconhecido"))
                duration = info.get("duration", 0)
                filesize = os.path.getsize(filename) if os.path.exists(filename) else 0

                # Verifica tamanho (limite Discord: 25MB sem Nitro, 500MB com Nitro)
                if filesize > 25 * 1024 * 1024:
                    # Arquivo muito grande para enviar diretamente
                    embed = discord.Embed(
                        title=f"📥 {platform.upper()} — {title[:80]}",
                        description=(
                            f"📹 **Vídeo:** {title[:200]}\n"
                            f"👤 **Uploader:** {uploader}\n"
                            f"⏱ **Duração:** {self._format_duration(duration)}\n"
                            f"📦 **Tamanho:** {filesize / 1024 / 1024:.1f} MB\n\n"
                            f"⚠ O arquivo é muito grande para enviar pelo Discord "
                            f"(limite de 25MB). O download foi salvo no servidor."
                        ),
                        color=0x4F8FFF,
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    # Envia o arquivo
                    file_ext = "mp3" if is_audio else "mp4"
                    with open(filename, "rb") as f:
                        discord_file = discord.File(f, filename=f"shaz_{platform}.{file_ext}")
                        
                        embed = discord.Embed(
                            title=f"📥 Download concluído — {platform.upper()}",
                            description=f"**{title[:200]}**\n👤 {uploader} | ⏱ {self._format_duration(duration)}",
                            color=0x4F8FFF,
                        )
                        embed.set_footer(text=f"Shaz AI • Video Download • {filesize / 1024 / 1024:.1f} MB")
                        await interaction.followup.send(embed=embed, file=discord_file)

                # Limpa arquivo temporário
                try:
                    os.unlink(filename)
                except Exception:
                    pass

        except Exception as e:
            log.error(f"/video error: {e}")
            error_msg = str(e)
            if "Private video" in error_msg:
                msg = "Este vídeo é privado e não pode ser baixado."
            elif "Video unavailable" in error_msg:
                msg = "Este vídeo não está disponível ou foi removido."
            elif "HTTP Error 403" in error_msg:
                msg = "Acesso negado ao vídeo. Pode ser restrito por região."
            else:
                msg = f"Erro ao baixar: {error_msg[:200]}"
            
            await interaction.followup.send(embed=error_embed(msg))

    def _format_duration(self, seconds: int) -> str:
        """Formata segundos para mm:ss ou hh:mm:ss."""
        h, remainder = divmod(seconds, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}h{m:02d}m{s:02d}s"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def _is_video_url(text: str) -> bool:
        """Verifica rapidamente se um texto contém URL de vídeo."""
        for platform, patterns in URL_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, text):
                    return True
        return False


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VideoCog(bot))