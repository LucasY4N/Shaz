"""
discord_bot/bot/voice/voice_manager.py
Gerenciador de voz do bot Discord.
Responsabilidade única: entrar/sair de canais de voz e reproduzir áudio.

Fluxo de TTS no Discord:
  1. /falar <texto> é chamado
  2. VoiceManager pede áudio ao ShazClient (backend TTS)
  3. Se não tiver áudio do backend, usa edge-tts local como fallback
  4. Reproduz o áudio no canal via FFmpeg (discord.py padrão)
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
from typing import Optional

import discord
from discord.ext import commands

from discord_bot.config.settings import get_discord_settings
from discord_bot.utils.logger import log


class VoiceManager:
    """
    Gerencia conexões de voz e reprodução de áudio no Discord.
    Uma instância por bot.
    """

    def __init__(self, bot: commands.Bot, shaz_client) -> None:
        self.bot = bot
        self.shaz = shaz_client
        self.settings = get_discord_settings()
        self._voice_clients: dict[int, discord.VoiceClient] = {}  # guild_id → VoiceClient
        self._auto_leave_tasks: dict[int, asyncio.Task] = {}

    # ── Entrar / Sair ─────────────────────────────────────────────────────

    async def join(self, channel: discord.VoiceChannel) -> discord.VoiceClient:
        """Entra em um canal de voz. Se já estiver em outro, move."""
        guild_id = channel.guild.id

        # Já está conectado neste servidor?
        existing = self._voice_clients.get(guild_id)
        if existing and existing.is_connected():
            if existing.channel.id == channel.id:
                return existing
            await existing.move_to(channel)
            log.info(f"Movido para canal: {channel.name}")
            return existing

        # Conecta novo
        vc = await channel.connect(timeout=15.0, reconnect=True)
        self._voice_clients[guild_id] = vc
        log.info(f"Entrou no canal de voz: {channel.name} ({channel.guild.name})")

        # Agenda saída automática após inatividade
        self._schedule_auto_leave(guild_id)
        return vc

    async def leave(self, guild_id: int) -> bool:
        """Sai do canal de voz de um servidor."""
        vc = self._voice_clients.get(guild_id)
        if not vc:
            return False

        self._cancel_auto_leave(guild_id)

        if vc.is_playing():
            vc.stop()

        await vc.disconnect()
        del self._voice_clients[guild_id]
        log.info(f"Saiu do canal de voz no servidor {guild_id}")
        return True

    def is_connected(self, guild_id: int) -> bool:
        vc = self._voice_clients.get(guild_id)
        return bool(vc and vc.is_connected())

    def get_voice_client(self, guild_id: int) -> Optional[discord.VoiceClient]:
        return self._voice_clients.get(guild_id)

    # ── Reprodução de áudio ───────────────────────────────────────────────

    async def speak(self, guild_id: int, text: str) -> bool:
        """
        Sintetiza texto e reproduz no canal de voz.

        Tenta:
        1. Pedir áudio ao backend Shaz (TTS real)
        2. Fallback: gerar com edge-tts localmente
        """
        vc = self._voice_clients.get(guild_id)
        if not vc or not vc.is_connected():
            log.warning(f"speak() chamado sem conexão de voz no servidor {guild_id}")
            return False

        # Aguarda se já estiver tocando
        if vc.is_playing():
            vc.stop()
            await asyncio.sleep(0.3)

        audio_bytes = await self._get_audio(text)
        if not audio_bytes:
            log.error("Nenhum áudio disponível para reproduzir")
            return False

        await self._play_bytes(vc, audio_bytes)
        self._reset_auto_leave(guild_id)
        return True

    async def _get_audio(self, text: str) -> Optional[bytes]:
        """Tenta obter áudio do backend, fallback para edge-tts local."""
        # Tenta backend primeiro
        audio = await self.shaz.synthesize_voice(text)
        if audio:
            log.debug(f"Áudio obtido do backend: {len(audio)} bytes")
            return audio

        # Fallback: edge-tts local
        return await self._synthesize_edge_tts(text)

    async def _synthesize_edge_tts(self, text: str) -> Optional[bytes]:
        """Sintetiza localmente com edge-tts como fallback."""
        try:
            import edge_tts

            voice = self.settings.tts_voice if hasattr(self.settings, "tts_voice") else "pt-BR-FranciscaNeural"
            communicate = edge_tts.Communicate(text, voice=voice)

            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])

            audio = buf.getvalue()
            if audio:
                log.debug(f"Áudio gerado via edge-tts local: {len(audio)} bytes")
                return audio
            return None

        except ImportError:
            log.error("edge-tts não instalado: pip install edge-tts")
            return None
        except Exception as e:
            log.error(f"edge-tts error: {e}")
            return None

    async def _play_bytes(self, vc: discord.VoiceClient, audio_bytes: bytes) -> None:
        """Reproduz bytes de áudio no canal de voz usando FFmpeg."""
        # Salva em arquivo temporário (FFmpeg precisa de arquivo)
        suffix = ".mp3" if audio_bytes[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3") else ".wav"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            done_event = asyncio.Event()

            def after_play(error):
                if error:
                    log.error(f"Erro na reprodução: {error}")
                done_event.set()

            source = discord.FFmpegPCMAudio(
                tmp_path,
                options="-vn",
            )
            vc.play(source, after=after_play)

            # Aguarda terminar (com timeout de 60s)
            await asyncio.wait_for(done_event.wait(), timeout=60.0)

        except asyncio.TimeoutError:
            log.warning("Timeout na reprodução de áudio")
            if vc.is_playing():
                vc.stop()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    # ── Auto-leave ────────────────────────────────────────────────────────

    def _schedule_auto_leave(self, guild_id: int) -> None:
        self._cancel_auto_leave(guild_id)
        task = asyncio.create_task(self._auto_leave_after(guild_id))
        self._auto_leave_tasks[guild_id] = task

    def _reset_auto_leave(self, guild_id: int) -> None:
        """Reinicia o timer de saída automática após atividade."""
        self._schedule_auto_leave(guild_id)

    def _cancel_auto_leave(self, guild_id: int) -> None:
        task = self._auto_leave_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    async def _auto_leave_after(self, guild_id: int) -> None:
        """Sai do canal automaticamente após inatividade."""
        try:
            await asyncio.sleep(self.settings.voice_auto_leave_seconds)
            vc = self._voice_clients.get(guild_id)
            if vc and vc.is_connected() and not vc.is_playing():
                log.info(f"Auto-leave após inatividade no servidor {guild_id}")
                await self.leave(guild_id)
        except asyncio.CancelledError:
            pass
