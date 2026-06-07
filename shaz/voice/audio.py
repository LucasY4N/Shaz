"""
shaz/voice/audio.py
Módulo de áudio para captura e reprodução.
Gerencia microfone e saída de áudio com sounddevice/pyaudio/pygame.
"""
from __future__ import annotations

import queue
import io
import os
import tempfile
import time
import wave
from collections import deque
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
        self._input_device = self._config.audio_input_device
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

            audio_queue: queue.Queue[Any] = queue.Queue()
            pre_roll_chunks = max(1, int((self._sample_rate / self._chunk_size) * 0.4))
            pre_roll: deque[Any] = deque(maxlen=pre_roll_chunks)
            speech_chunks: list[Any] = []

            energy_threshold = float(self._config.get("voice.stt_energy_threshold", 1000))
            pause_threshold = float(self._config.get("voice.stt_pause_threshold", 1.0))
            adjust_noise = bool(self._config.get("voice.stt_adjust_for_ambient_noise", True))
            phrase_limit = float(self._config.get("voice.stt_phrase_time_limit", phrase_limit))

            def on_audio(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                if status:
                    logger.warning(f"[Audio] Input status: {status}")
                audio_queue.put(indata.copy())

            logger.stt("Listening for speech...")

            with sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype="int16",
                blocksize=self._chunk_size,
                device=self._input_device,
                callback=on_audio,
            ):
                if adjust_noise:
                    calibration_chunks: list[Any] = []
                    calibration_end = time.monotonic() + 0.6
                    while time.monotonic() < calibration_end:
                        try:
                            calibration_chunks.append(audio_queue.get(timeout=0.1))
                        except queue.Empty:
                            pass
                    if calibration_chunks:
                        ambient_level = max(self._audio_rms(chunk) for chunk in calibration_chunks)
                        energy_threshold = max(energy_threshold, ambient_level * 2.0)
                        logger.stt(f"Ambient noise calibrated | threshold={energy_threshold:.0f}")

                start_deadline = time.monotonic() + timeout
                started_at: Optional[float] = None
                last_voice_at: Optional[float] = None

                while True:
                    now = time.monotonic()

                    if started_at is None and now >= start_deadline:
                        logger.stt("Listening timed out without speech")
                        return None

                    if started_at is not None and now - started_at >= phrase_limit:
                        logger.stt("Phrase time limit reached")
                        break

                    try:
                        chunk = audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    energy = self._audio_rms(chunk)

                    if started_at is None:
                        pre_roll.append(chunk)
                        if energy >= energy_threshold:
                            started_at = now
                            last_voice_at = now
                            speech_chunks.extend(pre_roll)
                            logger.stt("Speech detected")
                        continue

                    speech_chunks.append(chunk)
                    if energy >= energy_threshold:
                        last_voice_at = now
                    elif last_voice_at is not None and now - last_voice_at >= pause_threshold:
                        logger.stt("Silence detected, finishing recording")
                        break

            if not speech_chunks:
                return None

            recording = np.concatenate(speech_chunks, axis=0)

            buffer = io.BytesIO()
            with wave.open(buffer, "wb") as wf:
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

    @staticmethod
    def _audio_rms(chunk: Any) -> float:
        """Calcula energia RMS de um bloco PCM int16."""
        import numpy as np

        values = chunk.astype(np.float32)
        if values.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(np.square(values))))

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
                device=self._input_device,
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

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._output_device = self._config.audio_output_device
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
            suffix = self._detect_audio_suffix(audio_bytes)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name

            self._is_playing = True
            if suffix == ".mp3":
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    pygame.time.wait(100)

                pygame.mixer.music.stop()
            else:
                sound = pygame.mixer.Sound(temp_path)
                sound.play()

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
            suffix = self._detect_audio_suffix(audio_bytes)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
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
                sd.play(data, sr, device=self._output_device)
                sd.wait()
                return
            except Exception:
                pass

        logger.warning("[Audio] No playback method available. Install pygame or soundfile.")

    @staticmethod
    def _detect_audio_suffix(audio_bytes: bytes) -> str:
        """Detecta formato básico para salvar temporário com extensão correta."""
        if audio_bytes.startswith(b"RIFF"):
            return ".wav"
        if audio_bytes.startswith(b"ID3") or (
            len(audio_bytes) > 2 and audio_bytes[0] == 0xFF and audio_bytes[1] & 0xE0 == 0xE0
        ):
            return ".mp3"
        if audio_bytes.startswith(b"OggS"):
            return ".ogg"
        return ".wav"

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
        self.player = AudioPlayer(config)

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
