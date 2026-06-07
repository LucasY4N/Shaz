"""
shaz/voice/audio_voicemeeter.py
Extensão do AudioManager com suporte a VoiceMeeter.
Detecta automaticamente VoiceMeeter Input/Output e permite seleção de dispositivo.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from shaz.utils.logger import logger

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


def list_audio_devices() -> List[Dict[str, Any]]:
    """Lista todos os dispositivos de áudio disponíveis."""
    if not SOUNDDEVICE_AVAILABLE:
        return []
    devices = []
    for i, dev in enumerate(sd.query_devices()):
        devices.append({
            "index": i,
            "name": dev["name"],
            "inputs": dev["max_input_channels"],
            "outputs": dev["max_output_channels"],
            "sample_rate": int(dev["default_samplerate"]),
        })
    return devices


def find_voicemeeter_devices() -> Dict[str, Optional[int]]:
    """
    Detecta dispositivos VoiceMeeter automaticamente.
    Retorna índices dos dispositivos de entrada e saída.
    
    VoiceMeeter nomes possíveis:
      Saída TTS (Shaz fala):  'VoiceMeeter Input', 'VB-Audio VoiceMeeter VAIO'
      Entrada STT (Shaz ouve): 'VoiceMeeter Output', 'VB-Audio VoiceMeeter VAIO3'
    """
    result = {"output": None, "input": None, "output_name": None, "input_name": None}
    
    if not SOUNDDEVICE_AVAILABLE:
        return result

    OUTPUT_KEYWORDS = ["voicemeeter input", "vb-audio voicemeeter vaio", "cable input"]
    INPUT_KEYWORDS  = ["voicemeeter output", "vb-audio voicemeeter vaio3", "voicemeeter aux output", "cable output"]

    for i, dev in enumerate(sd.query_devices()):
        name_lower = dev["name"].lower()
        if result["output"] is None and dev["max_output_channels"] > 0:
            if any(k in name_lower for k in OUTPUT_KEYWORDS):
                result["output"] = i
                result["output_name"] = dev["name"]
                logger.tts(f"VoiceMeeter saída TTS encontrado: [{i}] {dev['name']}")
        if result["input"] is None and dev["max_input_channels"] > 0:
            if any(k in name_lower for k in INPUT_KEYWORDS):
                result["input"] = i
                result["input_name"] = dev["name"]
                logger.stt(f"VoiceMeeter entrada STT encontrado: [{i}] {dev['name']}")

    return result


def play_audio_to_device(audio_bytes: bytes, device_index: Optional[int] = None,
                          sample_rate: int = 24000) -> bool:
    """
    Reproduz áudio em bytes para um dispositivo específico (ex: VoiceMeeter Input).
    Retorna True se reproduziu com sucesso.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return False
    try:
        import soundfile as sf
        import io
        data, sr = sf.read(io.BytesIO(audio_bytes))
        sd.play(data, sr, device=device_index)
        sd.wait()
        return True
    except Exception as e:
        logger.error(f"[Audio] Erro ao reproduzir no dispositivo {device_index}: {e}")
        return False


def record_from_device(device_index: Optional[int], duration: float = 10.0,
                        sample_rate: int = 16000) -> Optional[bytes]:
    """
    Grava áudio de um dispositivo específico (ex: VoiceMeeter Output).
    Retorna bytes WAV.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return None
    try:
        import wave, io as _io
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='int16',
            device=device_index,
        )
        sd.wait()
        buf = _io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(recording.tobytes())
        return buf.getvalue()
    except Exception as e:
        logger.error(f"[Audio] Erro ao gravar do dispositivo {device_index}: {e}")
        return None
