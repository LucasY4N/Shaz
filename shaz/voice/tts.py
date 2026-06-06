"""
shaz/voice/tts.py
Síntese de voz para a Shaz.
Implementa XTTS-v2 como primário, com fallback automático para Piper TTS e Edge TTS.
Voz feminina, natural, amigável, jovem e de alta qualidade.
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

# ─── Tentativa de importar XTTS ─────────────────────────────────────────

try:
    from TTS.api import TTS as XTTSAPI
    XTTS_AVAILABLE = True
    logger.tts("XTTS available")
except ImportError:
    XTTS_AVAILABLE = False
    logger.tts("XTTS not available (Edge TTS will be used as primary)")

# ─── Tentativa de importar edge-tts ─────────────────────────────────────

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False


class XTTSSynthesizer:
    """
    Síntese de voz usando XTTS-v2.
    Voz feminina natural e de alta qualidade.
    """

    _instance = None

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._xtts_config = self._config.get_xtts_config()
        self._model = None
        self._speaker_wav = self._xtts_config.get(
            "speaker_wav", "assets/voices/shaz_reference.wav"
        )
        self._language = self._xtts_config.get("language", "pt")

    def _load_model(self) -> bool:
        """Carrega o modelo XTTS (lazy loading)."""
        if self._model is not None:
            return True

        if not XTTS_AVAILABLE:
            return False

        try:
            logger.tts("Loading XTTS-v2 model...")
            self._model = XTTSAPI("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
            logger.tts("XTTS-v2 model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"[TTS] Failed to load XTTS model: {e}")
            self._model = None
            return False

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto em áudio usando XTTS-v2.

        Args:
            text: Texto para sintetizar

        Returns:
            Áudio WAV em bytes ou None em caso de falha
        """
        # XTTS é pesado e síncrono, rodamos em uma thread para não travar o loop de eventos
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> Optional[bytes]:
        """
        Execução síncrona do XTTS (chamada via thread).
        """
        if not self._load_model():
            logger.tts("XTTS not available")
            return None

        try:
            # Verifica se o arquivo de speaker reference existe
            speaker_path = Path(self._speaker_wav)
            speaker_exists = speaker_path.exists()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

            # Define parâmetros
            tts_kwargs = {
                "text": text,
                "file_path": output_path,
                "language": self._language,
                "temperature": self._xtts_config.get("temperature", 0.75),
                "speed": self._xtts_config.get("speed", 1.0),
                "enable_text_splitting": self._xtts_config.get("enable_text_splitting", True),
            }

            # Adiciona speaker_wav se existir
            if speaker_exists:
                tts_kwargs["speaker_wav"] = str(speaker_path)
                logger.tts(f"Using speaker reference: {speaker_path}")
            else:
                logger.tts("No speaker reference found, using default voice")
                # XTTS precisa de speaker_wav; se não tiver, tenta speaker embedding
                tts_kwargs["speaker"] = self._config.voice_speaker or "shaz"

            self._model.tts_to_file(**tts_kwargs)

            # Lê o áudio gerado
            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            # Limpa arquivo temporário
            try:
                os.unlink(output_path)
            except Exception:
                pass

            logger.tts(f"XTTS synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"[TTS] XTTS synthesis error: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return XTTS_AVAILABLE


# ─── Piper TTS ────────────────────────────────────────────────────────────

class PiperSynthesizer:
    """
    Síntese de voz usando Piper TTS.
    Fallback caso XTTS não esteja disponível.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._piper_config = self._config.get_piper_config()
        self._model_path = Path(self._piper_config.get("model_path", "models/piper"))
        self._voice = self._piper_config.get("voice", "pt_BR-faber-medium")

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto em áudio usando Piper TTS via CLI.

        Args:
            text: Texto para sintetizar

        Returns:
            Áudio WAV em bytes ou None em caso de falha
        """
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> Optional[bytes]:
        """
        Execução síncrona do Piper (chamada via thread).
        """
        try:
            # Caminho do modelo Piper
            model_file = self._model_path / f"{self._voice}.onnx"
            config_file = self._model_path / f"{self._voice}.json"

            if not model_file.exists():
                logger.tts(f"Piper model not found: {model_file}")
                return None

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                output_path = f.name

            # Executa Piper via CLI
            cmd = [
                "piper",
                "--model", str(model_file),
                "--config", str(config_file) if config_file.exists() else "",
                "--output_file", output_path,
                "--noise_scale", str(self._piper_config.get("noise_scale", 0.667)),
                "--noise_w", str(self._piper_config.get("noise_w", 0.8)),
                "--length_scale", str(self._piper_config.get("length_scale", 1.0)),
            ]

            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if proc.returncode != 0:
                logger.error(f"[TTS] Piper error: {proc.stderr.decode()}")
                return None

            with open(output_path, "rb") as f:
                audio_bytes = f.read()

            try:
                os.unlink(output_path)
            except Exception:
                pass

            logger.tts(f"Piper synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
            return audio_bytes

        except FileNotFoundError:
            logger.warning("[TTS] Piper CLI not found. Install piper-tts.")
            return None
        except subprocess.TimeoutExpired:
            logger.error("[TTS] Piper synthesis timed out")
            return None
        except Exception as e:
            logger.error(f"[TTS] Piper synthesis error: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return self._model_path.exists() and any(
            self._model_path.glob("*.onnx")
        )


# ─── Edge TTS ─────────────────────────────────────────────────────────────

class EdgeSynthesizer:
    """
    Síntese de voz usando Microsoft Edge TTS.
    Fallback final, funciona sem modelos locais.
    Voz: pt-BR-FranciscaNeural (feminina, natural, brasileira).
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._edge_config = self._config.get_edge_config()
        self._voice = self._config.tts_voice or self._edge_config.get(
            "voice", "pt-BR-FranciscaNeural"
        )
        self._rate = self._edge_config.get("rate", "+0%")
        self._volume = self._edge_config.get("volume", "+0%")
        self._pitch = self._edge_config.get("pitch", "+0Hz")

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto em áudio usando Edge TTS.

        Args:
            text: Texto para sintetizar

        Returns:
            Áudio em bytes ou None em caso de falha
        """
        if not EDGE_TTS_AVAILABLE:
            logger.warning("[TTS] edge-tts not installed. Install with: pip install edge-tts")
            return None

        try:
            # Agora usamos o loop atual diretamente, sem asyncio.run()
            communicate = edge_tts.Communicate(
                text,
                voice=self._voice,
                rate=self._rate,
                volume=self._volume,
                pitch=self._pitch,
            )

            # Salva em buffer de bytes de forma assíncrona
            audio_bytes_io = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes_io.write(chunk["data"])

            audio_bytes = audio_bytes_io.getvalue()
            logger.tts(f"Edge TTS synthesized {len(text)} chars -> {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            logger.error(f"[TTS] Edge TTS error: {e}")
            return None

    async def list_voices(self) -> list:
        """Lista as vozes disponíveis no Edge TTS."""
        if not EDGE_TTS_AVAILABLE:
            return []

        try:
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["ShortName"],
                    "locale": v["Locale"],
                    "gender": v["Gender"],
                }
                for v in voices
            ]
        except Exception as e:
            logger.error(f"[TTS] Edge list voices error: {e}")
            return []

    @property
    def is_available(self) -> bool:
        return EDGE_TTS_AVAILABLE


# ─── TTS Manager com Fallback ─────────────────────────────────────────────

class TTSManager:
    """
    Gerenciador de síntese de voz com fallback automático.
    Tenta XTTS -> Piper -> Edge TTS em ordem.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._fallback_chain = self._config.voice_fallback_chain

        # Inicializa sintetizadores
        self._synthesizers = {
            "xtts": XTTSSynthesizer(config),
            "piper": PiperSynthesizer(config),
            "edge": EdgeSynthesizer(config),
        }

        self._current_engine = self._config.voice_model
        logger.tts(f"TTS Manager initialized | primary: {self._current_engine} | fallback: {self._fallback_chain}")

    async def synthesize(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto em áudio, tentando cada engine da cadeia de fallback.

        Args:
            text: Texto para sintetizar

        Returns:
            Áudio WAV em bytes ou None se todos falharem
        """
        if not text or not text.strip():
            logger.tts("Empty text, nothing to synthesize")
            return None

        # Tenta o engine primário primeiro
        engines_to_try = [self._current_engine]
        for engine in self._fallback_chain:
            if engine not in engines_to_try:
                engines_to_try.append(engine)

        for engine_name in engines_to_try:
            synthesizer = self._synthesizers.get(engine_name)
            if synthesizer is None:
                continue

            if not synthesizer.is_available:
                logger.tts(f"{engine_name.upper()} not available, trying next...")
                continue

            logger.tts(f"Synthesizing with {engine_name.upper()}...")
            audio = await synthesizer.synthesize(text)

            if audio and len(audio) > 100:
                logger.tts(f"Successfully synthesized with {engine_name.upper()}")
                return audio

            logger.tts(f"{engine_name.upper()} failed, trying next engine...")

        logger.error("[TTS] All TTS engines failed")
        return None

    async def speak(self, text: str) -> Optional[bytes]:
        """Alias para synthesize."""
        return await self.synthesize(text)

    @property
    def available_engines(self) -> list:
        """Lista os engines disponíveis."""
        return [
            name for name, synth in self._synthesizers.items()
            if synth.is_available
        ]

    def set_engine(self, engine: str) -> bool:
        """Define o engine primário de TTS."""
        if engine in self._synthesizers:
            self._current_engine = engine
            logger.tts(f"TTS engine set to: {engine}")
            return True
        return False

    async def get_edge_voices(self) -> list:
        """Obtém lista de vozes Edge TTS disponíveis."""
        edge = self._synthesizers.get("edge")
        if edge and edge.is_available:
            return await edge.list_voices()
        return []


# ─── Factory ──────────────────────────────────────────────────────────────

class TTSFactory:
    """Factory para criar instância TTS."""

    @staticmethod
    def create(config: Optional[Config] = None) -> TTSManager:
        """Cria o gerenciador TTS apropriado."""
        return TTSManager(config)


__all__ = [
    "TTSManager",
    "XTTSSynthesizer",
    "PiperSynthesizer",
    "EdgeSynthesizer",
    "TTSFactory",
]