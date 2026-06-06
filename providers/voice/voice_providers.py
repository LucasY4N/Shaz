"""
providers/voice/voice_providers.py
STT (Speech-to-Text) e TTS (Text-to-Speech) com suporte a VoiceMeeter.
Fluxo: Microfone → VoiceMeeter → STT → IA → TTS → VoiceMeeter → Saída

NOTA WINDOWS: pyaudio requer instalação separada.
  pip install pipwin && pipwin install pyaudio
  OU use install_windows.bat
"""
from __future__ import annotations
import asyncio
from core.entities.models import VoiceEmotion
from core.ports.interfaces import STTPort, TTSPort
from infrastructure.logging.logger import logger

# pyaudio é opcional — o resto do sistema funciona sem ele
try:
    import pyaudio as _pyaudio  # noqa: F401
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning(
        "[Voice] pyaudio não encontrado. Modo de voz desabilitado. "
        "Instale com: pip install pipwin && pipwin install pyaudio"
    )


# ─── STT Providers ───────────────────────────────────────────────────────────

class GoogleSTTProvider(STTPort):
    """STT via Google Speech Recognition. Requer pyaudio para microfone."""

    def __init__(self) -> None:
        import speech_recognition as sr
        self._recognizer = sr.Recognizer()
        self._sr = sr
        if not PYAUDIO_AVAILABLE:
            logger.warning("[STT] pyaudio ausente — listen() não funcionará")
        logger.info("[STT] GoogleSTT initialized")

    async def listen(self) -> str:
        """Captura áudio do microfone e transcreve."""
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "pyaudio não instalado. No Windows: pip install pipwin && pipwin install pyaudio"
            )
        sr = self._sr
        recognizer = self._recognizer

        def _sync_listen() -> str:
            with sr.Microphone() as source:
                logger.debug("[STT] ajustando ruído ambiente...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.debug("[STT] ouvindo...")
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
            try:
                text = recognizer.recognize_google(audio, language="pt-BR")
                logger.info(f"[STT] transcrito: {text}")
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                logger.error(f"[STT] Google API error: {e}")
                return ""

        return await asyncio.to_thread(_sync_listen)

    async def transcribe_file(self, audio_path: str) -> str:
        """Transcreve arquivo de áudio (não requer pyaudio)."""
        sr = self._sr
        recognizer = self._recognizer

        def _sync_file() -> str:
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            try:
                return recognizer.recognize_google(audio, language="pt-BR")
            except Exception as e:
                logger.error(f"[STT] file transcription error: {e}")
                return ""

        return await asyncio.to_thread(_sync_file)


# ─── TTS Providers ───────────────────────────────────────────────────────────

class Pyttsx3TTSProvider(TTSPort):
    """TTS offline via pyttsx3. Funciona sem internet e sem pyaudio."""

    _EMOTION_CONFIG: dict[VoiceEmotion, dict[str, int]] = {
        VoiceEmotion.NEUTRAL: {"rate": 175, "volume_pct": 90},
        VoiceEmotion.HAPPY:   {"rate": 200, "volume_pct": 100},
        VoiceEmotion.SAD:     {"rate": 140, "volume_pct": 70},
        VoiceEmotion.EXCITED: {"rate": 220, "volume_pct": 100},
        VoiceEmotion.CALM:    {"rate": 155, "volume_pct": 80},
    }

    def __init__(self) -> None:
        import pyttsx3
        self._engine = pyttsx3.init()
        logger.info("[TTS] Pyttsx3 initialized")

    async def speak(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.NEUTRAL,
        profile: str = "default",
    ) -> None:
        cfg = self._EMOTION_CONFIG.get(emotion, self._EMOTION_CONFIG[VoiceEmotion.NEUTRAL])

        def _sync_speak() -> None:
            self._engine.setProperty("rate", cfg["rate"])
            self._engine.setProperty("volume", cfg["volume_pct"] / 100)
            self._engine.say(text)
            self._engine.runAndWait()

        logger.debug(f"[TTS] speaking emotion={emotion.value} | text={text[:40]}...")
        await asyncio.to_thread(_sync_speak)

    async def to_audio_bytes(self, text: str, emotion: VoiceEmotion) -> bytes:
        import tempfile, os

        def _sync() -> bytes:
            cfg = self._EMOTION_CONFIG.get(emotion, self._EMOTION_CONFIG[VoiceEmotion.NEUTRAL])
            self._engine.setProperty("rate", cfg["rate"])
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            self._engine.save_to_file(text, path)
            self._engine.runAndWait()
            with open(path, "rb") as f:
                data = f.read()
            os.unlink(path)
            return data

        return await asyncio.to_thread(_sync)
