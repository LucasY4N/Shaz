"""
shaz/voice/voice_manager.py
Gerenciador unificado de voz que integra TTS normal + clonagem de voz.
Edge TTS como motor principal (sempre disponível).
Voice Cloner (XTTS) como motor opcional para vozes clonadas.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from shaz.core.config import Config
from shaz.utils.logger import logger

# Tenta importar o clonador de voz (opcional)
try:
    from shaz.voice.voice_cloner import VoiceCloner
    VOICE_CLONER_AVAILABLE = True
except ImportError:
    VOICE_CLONER_AVAILABLE = False
    logger.tts("VoiceCloner nao disponivel — use apenas vozes Edge TTS")


class VoiceManager:
    """
    Gerenciador unificado de voz.
    Integra Edge TTS (padrão) + clonagem de voz (opcional).

    Comportamento:
      - synthesize(): usa Edge TTS com a voz configurada
      - synthesize_cloned(): usa voz clonada se disponível
      - speak_on_demand(): só fala quando explicitamente solicitado
    """

    PROFILES_FILE = Path("data/voice_profiles/index.json")

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._cloner: Optional[VoiceCloner] = None

        # Edge TTS como motor primário
        from shaz.voice.tts import TTSFactory
        self._tts = TTSFactory.create(self._config)

        # Tenta carregar clonador opcional
        self._init_cloner()

        self._current_voice_type = "edge"  # "edge" ou "cloned"
        self._current_cloned_profile: Optional[str] = None

        logger.tts(
            f"VoiceManager iniciado | "
            f"clonagem={VOICE_CLONER_AVAILABLE} | "
            f"vozes_clonadas={len(self.list_cloned_profiles())}"
        )

    def _init_cloner(self) -> None:
        """Inicializa o clonador de voz se disponível."""
        if VOICE_CLONER_AVAILABLE:
            try:
                self._cloner = VoiceCloner()
            except Exception as e:
                logger.warning(f"[VoiceManager] Erro ao carregar VoiceCloner: {e}")
                self._cloner = None

    # ─── Síntese normal (Edge TTS) ─────────────────────────────────────

    async def synthesize(self, text: str) -> Optional[bytes]:
        """Sintetiza texto usando o motor TTS principal (Edge TTS)."""
        return await self._tts.synthesize(text)

    # ─── Síntese com voz clonada ───────────────────────────────────────

    async def synthesize_cloned(
        self,
        text: str,
        profile_id: Optional[str] = None,
        speed: float = 1.0,
        temperature: float = 0.75,
    ) -> Optional[bytes]:
        """
        Sintetiza usando uma voz clonada.

        Args:
            text: Texto para sintetizar
            profile_id: ID do perfil. Se None, usa o perfil ativo atual
            speed: Velocidade da fala (0.5-2.0)
            temperature: Variação da voz (0.1-1.0)

        Returns:
            Áudio WAV em bytes ou None
        """
        if not self._cloner:
            logger.warning("[VoiceManager] VoiceCloner nao disponivel")
            return None

        profile_id = profile_id or self._current_cloned_profile
        if not profile_id:
            logger.warning("[VoiceManager] Nenhum perfil de voz clonada selecionado")
            return None

        try:
            audio = await self._cloner.synthesize(
                text=text,
                profile_id=profile_id,
                speed=speed,
                temperature=temperature,
            )
            logger.tts(f"Cloned voice: {len(audio)} bytes | profile={profile_id}")
            return audio
        except Exception as e:
            logger.error(f"[VoiceManager] Erro clone: {e}")
            return None

    # ─── Gerenciamento de perfis clonados ──────────────────────────────

    def list_cloned_profiles(self) -> list:
        """Lista todos os perfis de voz clonada disponíveis."""
        if not self._cloner:
            return []
        return self._cloner.list_profiles()

    def get_cloned_profile(self, profile_id: str) -> Optional[object]:
        """Retorna um perfil clonado pelo ID."""
        if not self._cloner:
            return None
        return self._cloner.get_profile(profile_id)

    async def create_cloned_profile(
        self,
        audio_path: str,
        name: str,
        language: str = "pt",
        description: str = "",
    ) -> Optional[object]:
        """
        Cria um novo perfil de voz clonada.
        Retorna None se o clonador não estiver disponível.
        """
        if not self._cloner:
            logger.error(
                "[VoiceManager] VoiceCloner indisponivel.\n"
                "Instale com: pip install TTS\n"
                "(Requer Python 3.10 ou inferior)"
            )
            return None

        try:
            profile = await self._cloner.create_profile(
                audio_path=audio_path,
                name=name,
                language=language,
                description=description,
            )
            logger.tts(f"Perfil clonado criado: {profile.name} (ID: {profile.id})")
            return profile
        except Exception as e:
            logger.error(f"[VoiceManager] Erro ao criar perfil: {e}")
            return None

    def delete_cloned_profile(self, profile_id: str) -> bool:
        """Remove um perfil de voz clonada."""
        if not self._cloner:
            return False
        return self._cloner.delete_profile(profile_id)

    def set_active_cloned_profile(self, profile_id: Optional[str]) -> bool:
        """Define o perfil de voz clonada ativo."""
        if profile_id is None:
            self._current_cloned_profile = None
            self._current_voice_type = "edge"
            logger.tts("Voz clonada desativada, usando Edge TTS")
            return True

        if not self._cloner:
            return False

        profile = self._cloner.get_profile(profile_id)
        if not profile:
            logger.warning(f"[VoiceManager] Perfil '{profile_id}' nao encontrado")
            return False

        self._current_cloned_profile = profile_id
        self._current_voice_type = "cloned"
        logger.tts(f"Voz clonada ativada: {profile.name}")
        return True

    # ─── Fallback inteligente ──────────────────────────────────────────

    async def speak_text(self, text: str) -> Optional[bytes]:
        """
        Fala o texto usando a voz ativa (clonada ou Edge TTS).
        Se a voz clonada falhar, faz fallback para Edge TTS.
        """
        audio: Optional[bytes] = None

        if self._current_voice_type == "cloned" and self._current_cloned_profile:
            audio = await self.synthesize_cloned(text)

        if not audio:
            audio = await self.synthesize(text)

        return audio

    # ─── Utilitários ───────────────────────────────────────────────────

    def set_tts_engine(self, engine: str) -> bool:
        """Troca o motor TTS (edge, piper, xtts)."""
        return self._tts.set_engine(engine)

    def set_tts_voice(self, voice: str) -> None:
        """Define a voz do Edge TTS."""
        try:
            # EdgeSynthesizer não tem setter direto, recria
            from shaz.voice.tts import EdgeSynthesizer
            self._tts._synthesizers["edge"] = EdgeSynthesizer(self._config)
            # Força a voz
            edge = self._tts._synthesizers.get("edge")
            if edge:
                edge._voice = voice
                logger.tts(f"Voz Edge TTS alterada para: {voice}")
        except Exception as e:
            logger.error(f"[VoiceManager] Erro ao trocar voz: {e}")

    @property
    def tts(self):
        """Acesso ao TTSManager interno."""
        return self._tts

    @property
    def current_voice_type(self) -> str:
        return self._current_voice_type

    @property
    def is_cloned_voice_active(self) -> bool:
        return self._current_voice_type == "cloned" and self._current_cloned_profile is not None


__all__ = ["VoiceManager", "VOICE_CLONER_AVAILABLE"]