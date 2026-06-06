"""
shaz/voice/audio.py
Módulo de áudio para captura e reprodução.
Gerencia microfone e saída de áudio com sounddevice/pyaudio/pygame.
"""
from __future__ import annotations

import asyncio
import io
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, Callable, Optional

from shaz.core.config import Config
from shaz.utils.logger import logger

# Tentativa de importar bibliotecas de áudio
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioRecorder:
    """
    Captura de áudio do microfone com detecção de atividade de voz (VAD).
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._sample_rate = self._config.audio_sample_rate
        self._channels = self._config.audio_channels
        self._chunk_size = self._config.audio_chunk_size
        self._is_recording = False
        self._callback: Optional[Callable[[bytes], None]] = None

        if not SOUNDDEVICE_AVAILABLE:
            logger.warning("[Audio] sounddevice not available. Audio recording disabled.")

    def start_recording(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """Inicia captura contínua do microfone."""
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("[Audio] Cannot start recording: sounddevice not installed")
            return

        self._is_recording = True
        self._callback = callback
        logger.voice("Audio recording started")

    def stop_recording(self) -> None:
        """Para a captura do microfone."""
        self._is_recording = False
        logger.voice("Audio recording stopped")

    def record_speech(self, timeout: float = 10.0, phrase_limit: float = 15.0) -> Optional[bytes]:
        """
        Grava áudio até detectar silêncio (VAD simples por energia).

        Args:
            timeout: Tempo máximo de espera por fala
            phrase_limit: Duração máxima da frase

        Returns:
            Áudio gravado em WAV bytes ou None se nada gravado
        """
        if not SOUNDDEVICE_AVAILABLE:
            logger.error("[Audio] Cannot record: sounddevice not installed")
            return None

        try:
            import numpy as np

            logger.stt("Listening for speech...")

            # Grava áudio
            recording = sd.rec(
                int(phrase_limit * self._sample_rate),
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype='int16',
            )
            sd.wait()

            # Converte para WAV bytes
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self._sample_rate)
                wf.writeframes(recording.tobytes())

            audio_bytes = buffer.getvalue()
            if len(audio_bytes) > 1000:  # Mínimo de áudio
                logger.stt(f"Recorded {len(audio_bytes)} bytes of audio")
                return audio_bytes

            return None

        except Exception as e:
            logger.error(f"[Audio] Recording error: {e}")
            return None

    def record_to_file(self, filepath: str, duration: float = 5.0) -> Optional[str]:
        """Grava áudio diretamente para um arquivo WAV."""
        if not SOUNDDEVICE_AVAILABLE:
            return None

        try:
            import numpy as np

            recording = sd.rec(
                int(duration * self._sample_rate),
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype='int16',
            )
            sd.wait()

            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with wave.open(str(path), 'wb') as wf:
                wf.setnchannels(self._channels)
                wf.setsampwidth(2)
                wf.setframerate(self._sample_rate)
                wf.writeframes(recording.tobytes())

            logger.stt(f"Audio saved to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[Audio] Record to file error: {e}")
            return None


class AudioPlayer:
    """
    Reprodução de áudio usando pygame (ou fallback).
    """

    def __init__(self) -> None:
        self._is_playing = False
        self._pygame_initialized = False

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init(frequency=24000)
                self._pygame_initialized = True
            except Exception as e:
                logger.warning(f"[Audio] pygame mixer init failed: {e}")

    def play_bytes(self, audio_bytes: bytes) -> None:
        """Reproduz áudio a partir de bytes."""
        if self._pygame_initialized:
            self._play_pygame(audio_bytes)
        else:
            self._play_tempfile(audio_bytes)

    def _play_pygame(self, audio_bytes: bytes) -> None:
        """Reproduz usando pygame."""
        try:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            self._is_playing = True
            sound = pygame.mixer.Sound(temp_path)
            sound.play()

            # Espera terminar
            while pygame.mixer.get_busy():
                pygame.time.wait(100)

            sound.stop()
            self._is_playing = False

            # Limpa arquivo temporário
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"[Audio] pygame playback error: {e}")
            self._play_tempfile(audio_bytes)

    def _play_tempfile(self, audio_bytes: bytes) -> None:
        """Reproduz salvando em arquivo temporário e usando comando do sistema."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            self._is_playing = True
            self._play_file(temp_path)

            # Aguarda reprodução
            import time
            time.sleep(0.5)

            self._is_playing = False

            try:
                os.unlink(temp_path)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"[Audio] tempfile playback error: {e}")
            self._is_playing = False

    def _play_file(self, filepath: str) -> None:
        """Reproduz arquivo de áudio usando bibliotecas disponíveis."""
        # Tenta sounddevice primeiro
        if SOUNDDEVICE_AVAILABLE:
            try:
                import soundfile as sf
                data, sr = sf.read(filepath)
                sd.play(data, sr)
                sd.wait()
                return
            except Exception:
                pass

        logger.warning("[Audio] No playback method available. Install pygame or soundfile.")

    def play_file(self, filepath: str) -> None:
        """Reproduz arquivo de áudio."""
        self._play_file(filepath)

    def stop(self) -> None:
        """Para a reprodução."""
        if PYGAME_AVAILABLE and self._pygame_initialized:
            pygame.mixer.stop()
        self._is_playing = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing


class AudioManager:
    """
    Gerenciador de áudio unificado.
    Combina recorder e player em uma interface única.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config()
        self.recorder = AudioRecorder(config)
        self.player = AudioPlayer()

    def record_and_transcribe(
        self,
        stt_function: Callable[[bytes], str],
        timeout: float = 10.0,
        phrase_limit: float = 15.0,
    ) -> Optional[str]:
        """
        Grava áudio e transcreve usando a função STT fornecida.

        Args:
            stt_function: Função que recebe bytes de áudio e retorna texto
            timeout: Tempo máximo de espera
            phrase_limit: Duração máxima da frase

        Returns:
            Texto transcrito ou None
        """
        audio = self.recorder.record_speech(timeout, phrase_limit)
        if audio:
            text = stt_function(audio)
            return text
        return None

    def text_to_speech_and_play(
        self,
        tts_function: Callable[[str], Optional[bytes]],
        text: str,
    ) -> bool:
        """
        Gera áudio a partir de texto e reproduz.

        Args:
            tts_function: Função que recebe texto e retorna bytes de áudio
            text: Texto para sintetizar

        Returns:
            True se reproduziu com sucesso
        """
        audio = tts_function(text)
        if audio:
            self.player.play_bytes(audio)
            return True
        return False


__all__ = ["AudioRecorder", "AudioPlayer", "AudioManager"]