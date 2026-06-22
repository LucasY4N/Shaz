"""
shaz/voice_cloner.py  ← substitua o arquivo existente

FIXES APLICADOS:
  1. Importação corrigida — funciona tanto de shaz.voice_cloner quanto de shaz/voice_cloner.py
  2. PROFILES_DIR agora é relativo à raiz do projeto, não ao CWD
  3. load_active_voice_preference() carrega automaticamente a preferência salva
  4. Método get_active_profile_id() para o server.py saber qual perfil está ativo
  5. Validação mais clara quando XTTS não está instalado
  6. synthesize() nunca vai silenciosamente falhar — levanta exceção com mensagem útil
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Localiza a raiz do projeto independente de onde o script for chamado
_THIS_FILE = Path(__file__).resolve()
# shaz/voice_cloner.py → raiz é o pai de shaz/
_PROJECT_ROOT = _THIS_FILE.parent.parent if _THIS_FILE.parent.name == "shaz" else _THIS_FILE.parent

try:
    from shaz.utils.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger("VoiceCloner")  # type: ignore

# ─── Checagem de dependências ─────────────────────────────────────────────
try:
    from TTS.api import TTS as XTTSAPI
    XTTS_AVAILABLE = True
except ImportError:
    XTTS_AVAILABLE = False
    try:
        logger.warning(
            "[VoiceCloner] XTTS (Coqui TTS) não instalado.\n"
            "Para clonar voz execute: pip install TTS\n"
            "Atenção: requer ~2GB de download e ~4GB de RAM."
        )
    except Exception:
        print("[VoiceCloner] XTTS não instalado: pip install TTS")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# ─── Modelos ─────────────────────────────────────────────────────────────

@dataclass
class VoiceProfile:
    id: str
    name: str
    reference_wav: str
    language: str
    created_at: str
    duration_seconds: float
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        return cls(**data)


# ─── Voice Cloner ─────────────────────────────────────────────────────────

class VoiceCloner:
    """
    Clonagem de voz usando XTTS-v2 (Coqui TTS).

    Uso rápido:
        cloner = VoiceCloner()
        profile = await cloner.create_profile("referencia.wav", "Minha Voz", language="pt")
        audio = await cloner.synthesize("Olá mundo!", profile.id)
        with open("saida.wav", "wb") as f:
            f.write(audio)
    """

    # Diretório de perfis relativo à raiz do projeto
    PROFILES_DIR = _PROJECT_ROOT / "data" / "voice_profiles"
    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(self, profiles_dir: Optional[Path] = None) -> None:
        self._profiles_dir = Path(profiles_dir) if profiles_dir else self.PROFILES_DIR
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._model: Optional[XTTSAPI] = None
        self._profiles: dict[str, VoiceProfile] = {}
        self._active_id: Optional[str] = None
        self._load_profiles()
        self._load_active_preference()

    # ─── Modelo ──────────────────────────────────────────────────────

    def _load_model(self) -> bool:
        if self._model is not None:
            return True
        if not XTTS_AVAILABLE:
            raise ImportError(
                "Coqui TTS (XTTS-v2) não está instalado!\n"
                "Execute: pip install TTS\n"
                "Nota: baixa ~2GB e requer ~4GB de RAM."
            )
        try:
            try:
                logger.info("[VoiceCloner] Carregando XTTS-v2...")
            except Exception:
                print("[VoiceCloner] Carregando XTTS-v2...")
            self._model = XTTSAPI(self.MODEL_NAME, gpu=False)
            try:
                logger.info("[VoiceCloner] XTTS-v2 pronto!")
            except Exception:
                print("[VoiceCloner] XTTS-v2 pronto!")
            return True
        except Exception as e:
            try:
                logger.error(f"[VoiceCloner] Falha ao carregar XTTS: {e}")
            except Exception:
                print(f"[VoiceCloner] Falha ao carregar XTTS: {e}")
            self._model = None
            return False

    # ─── Perfis ──────────────────────────────────────────────────────

    def _load_profiles(self) -> None:
        index_path = self._profiles_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._profiles = {
                    pid: VoiceProfile.from_dict(pdata)
                    for pid, pdata in data.items()
                }
                try:
                    logger.info(f"[VoiceCloner] {len(self._profiles)} perfis carregados de {self._profiles_dir}")
                except Exception:
                    pass
            except Exception as e:
                try:
                    logger.error(f"[VoiceCloner] Erro ao carregar perfis: {e}")
                except Exception:
                    print(f"[VoiceCloner] Erro ao carregar perfis: {e}")

    def _save_profiles(self) -> None:
        index_path = self._profiles_dir / "index.json"
        data = {pid: p.to_dict() for pid, p in self._profiles.items()}
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_active_preference(self) -> None:
        """Carrega a preferência de voz ativa salva pelo launcher."""
        pref_file = _PROJECT_ROOT / "data" / "voice_preference.txt"
        if pref_file.exists():
            try:
                pid = pref_file.read_text().strip()
                if pid and pid in self._profiles:
                    self._active_id = pid
                    try:
                        logger.info(f"[VoiceCloner] Voz ativa carregada: {self._profiles[pid].name}")
                    except Exception:
                        pass
            except Exception:
                pass

    def set_active(self, profile_id: Optional[str]) -> bool:
        """Define a voz ativa. profile_id=None volta ao padrão."""
        if profile_id is None:
            self._active_id = None
            # Remove preferência salva
            pref_file = _PROJECT_ROOT / "data" / "voice_preference.txt"
            if pref_file.exists():
                pref_file.unlink()
            return True
        if profile_id in self._profiles:
            self._active_id = profile_id
            pref_file = _PROJECT_ROOT / "data" / "voice_preference.txt"
            pref_file.parent.mkdir(parents=True, exist_ok=True)
            pref_file.write_text(profile_id)
            return True
        return False

    def get_active_profile_id(self) -> Optional[str]:
        return self._active_id

    def list_profiles(self) -> list[VoiceProfile]:
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        return self._profiles.get(profile_id)

    def delete_profile(self, profile_id: str) -> bool:
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        profile_dir = self._profiles_dir / profile_id
        if profile_dir.exists():
            shutil.rmtree(profile_dir)
        del self._profiles[profile_id]
        if self._active_id == profile_id:
            self.set_active(None)
        self._save_profiles()
        return True

    # ─── Pré-processamento ────────────────────────────────────────────

    def _convert_to_wav(self, input_path: str, output_path: str) -> bool:
        if not PYDUB_AVAILABLE:
            if str(input_path).lower().endswith(".wav"):
                shutil.copy(input_path, output_path)
                return True
            else:
                try:
                    logger.error(
                        "[VoiceCloner] pydub não instalado. Para MP3/OGG:\n"
                        "  pip install pydub\n  (também requer FFmpeg)"
                    )
                except Exception:
                    print("[VoiceCloner] Instale pydub: pip install pydub")
                # Tenta FFmpeg direto como fallback
                try:
                    import subprocess
                    result = subprocess.run(
                        ["ffmpeg", "-y", "-i", input_path,
                         "-acodec", "pcm_s16le", "-ac", "1", "-ar", "22050", output_path],
                        capture_output=True, timeout=30,
                    )
                    return result.returncode == 0
                except Exception:
                    return False
        try:
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_channels(1).set_frame_rate(22050)
            audio.export(output_path, format="wav")
            return True
        except Exception as e:
            try:
                logger.error(f"[VoiceCloner] Conversão falhou: {e}")
            except Exception:
                print(f"[VoiceCloner] Conversão falhou: {e}")
            return False

    def _get_audio_duration(self, wav_path: str) -> float:
        try:
            import wave
            with wave.open(wav_path, "r") as wf:
                return wf.getnframes() / float(wf.getframerate())
        except Exception:
            return 0.0

    def _validate_reference_audio(self, wav_path: str) -> tuple[bool, str]:
        duration = self._get_audio_duration(wav_path)
        if duration < 3.0:
            return False, f"Áudio muito curto ({duration:.1f}s). Mínimo: 6 segundos."
        if duration < 6.0:
            return True, f"⚠ Áudio curto ({duration:.1f}s). Recomendado: 6-30s."
        if duration > 30.0:
            return True, f"⚠ Áudio longo ({duration:.1f}s). XTTS usará os primeiros 30s."
        return True, f"✓ Duração ideal: {duration:.1f}s"

    # ─── Criação ─────────────────────────────────────────────────────

    async def create_profile(
        self,
        audio_path: str,
        name: str,
        language: str = "pt",
        description: str = "",
    ) -> VoiceProfile:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {audio_path}")

        if not XTTS_AVAILABLE:
            raise ImportError(
                "Coqui TTS não instalado.\nExecute: pip install TTS"
            )

        profile_id = str(uuid.uuid4())[:8]
        profile_dir = self._profiles_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)

        wav_path = str(profile_dir / "reference.wav")
        ok = await asyncio.to_thread(self._convert_to_wav, str(audio_path), wav_path)
        if not ok:
            shutil.rmtree(profile_dir, ignore_errors=True)
            raise ValueError(f"Não foi possível converter '{audio_path}' para WAV.")

        valid, msg = self._validate_reference_audio(wav_path)
        if not valid:
            shutil.rmtree(profile_dir, ignore_errors=True)
            raise ValueError(msg)

        try:
            logger.info(f"[VoiceCloner] {msg}")
        except Exception:
            print(f"[VoiceCloner] {msg}")

        duration = self._get_audio_duration(wav_path)
        profile = VoiceProfile(
            id=profile_id,
            name=name,
            reference_wav=wav_path,
            language=language,
            created_at=datetime.now().isoformat(),
            duration_seconds=duration,
            description=description,
        )
        self._profiles[profile_id] = profile
        self._save_profiles()
        try:
            logger.info(f"[VoiceCloner] Perfil '{name}' criado! ID: {profile_id}")
        except Exception:
            print(f"[VoiceCloner] Perfil '{name}' criado! ID: {profile_id}")
        return profile

    # ─── Síntese ─────────────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        profile_id: str,
        speed: float = 1.0,
        temperature: float = 0.75,
    ) -> bytes:
        if not XTTS_AVAILABLE:
            raise ImportError("Coqui TTS não instalado. Execute: pip install TTS")

        profile = self._profiles.get(profile_id)
        if not profile:
            available = list(self._profiles.keys())
            raise KeyError(
                f"Perfil '{profile_id}' não encontrado.\n"
                f"Perfis disponíveis: {available}"
            )

        if not Path(profile.reference_wav).exists():
            raise FileNotFoundError(
                f"Arquivo de referência não existe: {profile.reference_wav}\n"
                f"O perfil pode ter sido movido. Recrie-o com 'Clonar Nova Voz'."
            )

        return await asyncio.to_thread(
            self._synthesize_sync, text, profile, speed, temperature
        )

    def _synthesize_sync(
        self,
        text: str,
        profile: VoiceProfile,
        speed: float,
        temperature: float,
    ) -> bytes:
        if not self._load_model():
            raise RuntimeError("Não foi possível carregar XTTS-v2.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        try:
            self._model.tts_to_file(
                text=text,
                speaker_wav=profile.reference_wav,
                language=profile.language,
                file_path=output_path,
                speed=speed,
                temperature=temperature,
                enable_text_splitting=True,
            )
            with open(output_path, "rb") as f:
                audio_bytes = f.read()
            try:
                logger.info(f"[VoiceCloner] Sintetizou {len(audio_bytes)} bytes com '{profile.name}'")
            except Exception:
                pass
            return audio_bytes
        finally:
            try:
                os.unlink(output_path)
            except Exception:
                pass

    # ─── Utilidades ──────────────────────────────────────────────────

    async def synthesize_and_save(
        self,
        text: str,
        profile_id: str,
        output_path: str,
        **kwargs,
    ) -> str:
        audio_bytes = await self.synthesize(text, profile_id, **kwargs)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        return output_path

    def get_supported_languages(self) -> list[str]:
        return ["pt", "en", "es", "fr", "de", "it", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "hu", "ko", "ja", "hi"]

    def __repr__(self) -> str:
        return f"VoiceCloner(profiles={len(self._profiles)}, xtts={XTTS_AVAILABLE}, active={self._active_id})"
