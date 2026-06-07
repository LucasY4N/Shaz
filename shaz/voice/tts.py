"""
shaz/voice/tts.py  — VERSÃO CORRIGIDA
Fixes aplicados:
  1. Edge TTS não usa mais asyncio.run() dentro de loop existente
  2. Edge TTS definido como engine primário (mais confiável sem instalação)
  3. XTTS e Piper continuam como opções mas não travam o boot se ausentes
  4. Suporte a VoiceMeeter: AudioPlayer aceita nome/índice de dispositivo de saída
"""
from __future__ import annotations

import asyncio
import io
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from shaz.core.config import Config
from shaz.utils.logger import logger

try:
    from TTS.api import TTS as XTTSAPI
    XTTS_AVAILABLE = True
    logger.tts("XTTS disponível")
except ImportError:
    XTTS_AVAILABLE = False
    logger.tts("XTTS não instalado — Edge TTS será usado como primário")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.tts("edge-tts não instalado: pip install edge-tts")


# ─── XTTS ────────────────────────────────────────────────────────────────────

class XTTSSynthesizer:
    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._xtts_config = self._config.get_xtts_config()
        self._model = None
        self._speaker_wav = self._xtts_config.get("speaker_wav", "assets/voices/shaz_reference.wav")
        self._language = self._xtts_config.get("language", "pt")

    def _load_model(self) -> bool:
        if self._model is not None:
            return True
        if not XTTS_AVAILABLE:
            return False
        try:
            logger.tts("Carregando modelo XTTS-v2...")
            self._model = XTTSAPI("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            logger.tts("XTTS-v2 carregado")
            return True
        except Exception as e:
            logger.error(f"[TTS] Falha ao carregar XTTS: {e}")
            self._model = None
            return False

    async def synthesize(self, text: str) -> Optional[bytes]:
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> Optional[bytes]:
        if not self._load_model():
            return None
        try:
            speaker_path = Path(self._speaker_wav)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            tts_kwargs = {
                "text": text,
                "file_path": output_path,
                "language": self._language,
            }
            if speaker_path.exists():
                tts_kwargs["speaker_wav"] = str(speaker_path)
            else:
                tts_kwargs["speaker"] = self._config.voice_speaker or "shaz"
            self._model.tts_to_file(**tts_kwargs)
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            try:
                os.unlink(output_path)
            except Exception:
                pass
            logger.tts(f"XTTS sintetizou {len(text)} chars → {len(audio_bytes)} bytes")
            return audio_bytes
        except Exception as e:
            logger.error(f"[TTS] XTTS erro: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return XTTS_AVAILABLE


# ─── Piper ───────────────────────────────────────────────────────────────────

class PiperSynthesizer:
    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._piper_config = self._config.get_piper_config()
        self._model_path = Path(self._piper_config.get("model_path", "models/piper"))
        self._voice = self._piper_config.get("voice", "pt_BR-faber-medium")

    async def synthesize(self, text: str) -> Optional[bytes]:
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> Optional[bytes]:
        try:
            model_file = self._model_path / f"{self._voice}.onnx"
            config_file = self._model_path / f"{self._voice}.json"
            if not model_file.exists():
                logger.tts(f"Modelo Piper não encontrado: {model_file}")
                return None
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name
            cmd = ["piper", "--model", str(model_file), "--output_file", output_path]
            if config_file.exists():
                cmd += ["--config", str(config_file)]
            proc = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=30)
            if proc.returncode != 0:
                logger.error(f"[TTS] Piper erro: {proc.stderr.decode()}")
                return None
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            try:
                os.unlink(output_path)
            except Exception:
                pass
            logger.tts(f"Piper sintetizou {len(text)} chars → {len(audio_bytes)} bytes")
            return audio_bytes
        except FileNotFoundError:
            logger.warning("[TTS] Piper CLI não encontrado")
            return None
        except Exception as e:
            logger.error(f"[TTS] Piper erro: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return self._model_path.exists() and any(self._model_path.glob("*.onnx"))


# ─── Edge TTS — FIX PRINCIPAL ────────────────────────────────────────────────

class EdgeSynthesizer:
    """
    FIX: Não usa mais asyncio.run() — roda direto no loop existente (coroutine pura).
    Isso resolve o conflito com o event loop do PySide6/asyncio já em execução.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._edge_config = self._config.get_edge_config()
        self._voice = self._config.tts_voice or self._edge_config.get("voice", "pt-BR-FranciscaNeural")
        self._rate = self._edge_config.get("rate", "+0%")
        self._volume = self._edge_config.get("volume", "+0%")
        self._pitch = self._edge_config.get("pitch", "+0Hz")

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        FIX: coroutine pura — sem asyncio.run() aninhado.
        Chamada diretamente com 'await', sem to_thread.
        """
        if not EDGE_TTS_AVAILABLE:
            logger.warning("[TTS] edge-tts não instalado: pip install edge-tts")
            return None

        try:
            communicate = edge_tts.Communicate(
                text,
                voice=self._voice,
                rate=self._rate,
                volume=self._volume,
                pitch=self._pitch,
            )

            audio_bytes_io = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes_io.write(chunk["data"])

            audio_bytes = audio_bytes_io.getvalue()

            if not audio_bytes:
                logger.error("[TTS] Edge TTS retornou áudio vazio")
                return None

            logger.tts(f"Edge TTS sintetizou {len(text)} chars → {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"[TTS] Edge TTS erro: {e}")
            return None

    async def list_voices(self) -> list:
        if not EDGE_TTS_AVAILABLE:
            return []
        try:
            voices = await edge_tts.list_voices()
            return [{"name": v["ShortName"], "locale": v["Locale"], "gender": v["Gender"]} for v in voices]
        except Exception as e:
            logger.error(f"[TTS] Edge list_voices erro: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return EDGE_TTS_AVAILABLE


# ─── TTSManager com VoiceMeeter ──────────────────────────────────────────────

class TTSManager:
    """
    Gerenciador TTS com suporte a VoiceMeeter.
    Fallback: Edge → Piper → XTTS (ordem de confiabilidade).
    VoiceMeeter: define output_device_name para rotear áudio para VoiceMeeter Input.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        # FIX: Edge TTS como primário — mais confiável sem instalação extra
        self._fallback_chain = ["edge", "piper", "xtts"]
        self._current_engine = "edge"

        self._synthesizers = {
            "xtts": XTTSSynthesizer(config),
            "piper": PiperSynthesizer(config),
            "edge": EdgeSynthesizer(config),
        }

        # VoiceMeeter: nome do dispositivo de saída (None = padrão do sistema)
        self._output_device: Optional[str] = None

        logger.tts(f"TTSManager iniciado | primário: {self._current_engine} | fallback: {self._fallback_chain}")

    def set_voicemeeter_output(self, device_name: Optional[str]) -> None:
        """
        Define o dispositivo de saída de áudio.
        Para VoiceMeeter: use 'VoiceMeeter Input' ou 'CABLE Input'.
        None = dispositivo padrão do sistema.
        """
        self._output_device = device_name
        logger.tts(f"Dispositivo de saída TTS: {device_name or 'padrão do sistema'}")

    async def synthesize(self, text: str) -> Optional[bytes]:
        if not text or not text.strip():
            return None

        engines_to_try = [self._current_engine] + [e for e in self._fallback_chain if e != self._current_engine]

        for engine_name in engines_to_try:
            synthesizer = self._synthesizers.get(engine_name)
            if synthesizer is None or not synthesizer.is_available:
                continue

            logger.tts(f"Sintetizando com {engine_name.upper()}...")
            audio = await synthesizer.synthesize(text)

            if audio and len(audio) > 100:
                return audio

            logger.tts(f"{engine_name.upper()} falhou, tentando próximo...")

        logger.error("[TTS] Todos os engines falharam")
        return None

    async def speak(self, text: str) -> Optional[bytes]:
        return await self.synthesize(text)

    def set_engine(self, engine: str) -> bool:
        if engine in self._synthesizers:
            self._current_engine = engine
            logger.tts(f"Engine TTS: {engine}")
            return True
        return False

    @property
    def available_engines(self) -> list:
        return [n for n, s in self._synthesizers.items() if s.is_available]

    @property
    def output_device(self) -> Optional[str]:
        return self._output_device

    async def get_edge_voices(self) -> list:
        edge = self._synthesizers.get("edge")
        if edge and edge.is_available:
            return await edge.list_voices()
        return []


class TTSFactory:
    @staticmethod
    def create(config: Optional[Config] = None) -> TTSManager:
        return TTSManager(config)


__all__ = ["TTSManager", "XTTSSynthesizer", "PiperSynthesizer", "EdgeSynthesizer", "TTSFactory"]
