"""
shaz/voice/stt.py
Reconhecimento de voz usando Faster-Whisper.
Suporte a VAD (Voice Activity Detection), redução de silêncio,
detecção automática de início/fim da fala, português e inglês.
"""
from __future__ import annotations

import io
import os
import tempfile
import wave
from pathlib import Path
from typing import Optional

from shaz.core.config import Config
from shaz.utils.logger import logger

# Tentativa de importar faster-whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("[STT] faster-whisper not installed. Install with: pip install faster-whisper")

# Tentativa de importar speech_recognition como fallback
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


class FasterWhisperSTT:
    """
    Reconhecimento de voz usando Faster-Whisper.
    Modelo local, rápido e preciso.
    Suporte a português e inglês com detecção automática.
    """

    _models: dict = {}

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._model_size = self._config.stt_model
        self._language = self._config.stt_language
        self._model = None
        self._device = "auto"

        if FASTER_WHISPER_AVAILABLE:
            self._load_model()
        else:
            logger.warning("[STT] Faster-Whisper unavailable. Will use fallback.")

    def _load_model(self) -> None:
        """Carrega o modelo Whisper."""
        try:
            # Detecta dispositivo
            try:
                import torch
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self._device = "cpu"

            # Verifica se o modelo já está carregado em cache
            model_key = f"{self._model_size}_{self._device}"
            if model_key in self._models:
                self._model = self._models[model_key]
                logger.stt(f"Using cached Whisper model: {self._model_size}")
                return

            logger.stt(f"Loading Whisper model: {self._model_size} on {self._device}...")
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type="float16" if self._device == "cuda" else "int8",
                cpu_threads=4,
                num_workers=2,
            )
            self._models[model_key] = self._model
            logger.stt(f"Whisper model loaded: {self._model_size}")
        except Exception as e:
            logger.error(f"[STT] Failed to load Whisper model: {e}")
            self._model = None

    def transcribe_bytes(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """
        Transcreve áudio a partir de bytes WAV.

        Args:
            audio_bytes: Áudio em formato WAV
            language: Código do idioma (pt, en, None para auto)

        Returns:
            Texto transcrito
        """
        if self._model and FASTER_WHISPER_AVAILABLE:
            return self._transcribe_faster(audio_bytes, language)
        else:
            return self._transcribe_fallback(audio_bytes, language)

    def _transcribe_faster(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """Transcrição usando Faster-Whisper."""
        try:
            # Salva bytes em arquivo temporário
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            lang = language or self._language or None

            segments, info = self._model.transcribe(
                temp_path,
                language=lang,
                beam_size=5,
                best_of=5,
                vad_filter=self._config.get("voice.vad_enabled", True),
                vad_parameters=dict(
                    threshold=self._config.get("voice.vad_threshold", 0.5),
                    min_speech_duration_ms=250,
                    max_speech_duration_s=float('inf'),
                    min_silence_duration_ms=500,
                ),
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
                condition_on_previous_text=True,
            )

            detected_lang = getattr(info, 'language', lang or 'unknown')
            logger.stt(f"Transcribed ({detected_lang}): ")

            text = " ".join(segment.text for segment in segments).strip()

            # Limpa arquivo temporário
            try:
                os.unlink(temp_path)
            except Exception:
                pass

            return text

        except Exception as e:
            logger.error(f"[STT] Faster-Whisper error: {e}")
            return ""

    def _transcribe_fallback(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """Fallback usando speech_recognition (Google STT)."""
        if not SR_AVAILABLE:
            logger.error("[STT] No STT engine available")
            return ""

        try:
            recognizer = sr.Recognizer()

            # Converte bytes para AudioData
            audio_file = io.BytesIO(audio_bytes)
            with sr.AudioFile(audio_file) as source:
                audio = recognizer.record(source)

            lang_code = {
                "pt": "pt-BR",
                "en": "en-US",
            }.get(language or self._language, "pt-BR")

            text = recognizer.recognize_google(audio, language=lang_code)
            logger.stt(f"Fallback transcribed: {text[:50]}...")
            return text

        except sr.UnknownValueError:
            logger.stt("Could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"[STT] Google API error: {e}")
            return ""
        except Exception as e:
            logger.error(f"[STT] Fallback error: {e}")
            return ""

    def transcribe_file(self, filepath: str, language: Optional[str] = None) -> str:
        """
        Transcreve arquivo de áudio.

        Args:
            filepath: Caminho do arquivo de áudio
            language: Código do idioma

        Returns:
            Texto transcrito
        """
        try:
            with open(filepath, "rb") as f:
                audio_bytes = f.read()
            return self.transcribe_bytes(audio_bytes, language)
        except Exception as e:
            logger.error(f"[STT] File read error: {e}")
            return ""

    @property
    def is_available(self) -> bool:
        return (FASTER_WHISPER_AVAILABLE and self._model is not None) or SR_AVAILABLE


# ─── Factory ──────────────────────────────────────────────────────────────

class STTFactory:
    """Factory para criar instância STT baseada na configuração."""

    @staticmethod
    def create(config: Optional[Config] = None) -> FasterWhisperSTT:
        """Cria a instância STT apropriada."""
        cfg = config or Config()
        engine = cfg.stt_engine

        if engine == "whisper" and FASTER_WHISPER_AVAILABLE:
            logger.stt(f"Using Faster-Whisper STT (model: {cfg.stt_model})")
            return FasterWhisperSTT(config)

        logger.stt(f"Using Whisper STT (model: {cfg.stt_model})")
        return FasterWhisperSTT(config)


__all__ = ["FasterWhisperSTT", "STTFactory"]
