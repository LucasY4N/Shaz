"""
shaz/voice/voice_cloner.py
Clonagem de voz para o Shaz AI.

Pipeline:
  1. Recebe um áudio de referência (WAV/MP3, 6-30s de fala limpa)
  2. Extrai o "embedding" da voz via XTTS-v2
  3. Salva o perfil de voz em disco (data/voice_profiles/)
  4. Usa o perfil salvo para sintetizar qualquer texto com aquela voz

Dependências obrigatórias:
  pip install TTS        # XTTS-v2 (clonagem local, offline)
  pip install edge-tts   # fallback online

Dependências opcionais para pré-processamento:
  pip install pydub      # conversão de formatos (MP3 → WAV, etc.)
  pip install librosa    # análise de qualidade do áudio
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

from shaz.utils.logger import logger

# ─── Checagem de dependências ─────────────────────────────────────────────

try:
    from TTS.api import TTS as XTTSAPI
    XTTS_AVAILABLE = True
except ImportError:
    XTTS_AVAILABLE = False
    logger.warning("[VoiceCloner] TTS não instalado. Execute: pip install TTS")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


# ─── Modelos de dados ─────────────────────────────────────────────────────

@dataclass
class VoiceProfile:
    """Perfil de voz clonada."""
    id: str
    name: str
    reference_wav: str          # Caminho do WAV de referência
    language: str               # pt, en, es, etc.
    created_at: str
    duration_seconds: float     # Duração do áudio de referência
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceProfile":
        return cls(**data)


# ─── Voice Cloner ─────────────────────────────────────────────────────────

class VoiceCloner:
    """
    Motor de clonagem de voz usando XTTS-v2.

    Uso básico:
        cloner = VoiceCloner()

        # 1. Criar perfil a partir de um áudio
        profile = await cloner.create_profile(
            audio_path="minha_voz.mp3",
            name="Minha Voz",
            language="pt"
        )

        # 2. Gerar áudio com a voz clonada
        audio_bytes = await cloner.synthesize(
            text="Olá! Isso é um teste de clonagem de voz.",
            profile_id=profile.id
        )

        # Salvar resultado
        with open("saida.wav", "wb") as f:
            f.write(audio_bytes)
    """

    PROFILES_DIR = Path("data/voice_profiles")
    MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(self, profiles_dir: Optional[Path] = None) -> None:
        self._profiles_dir = profiles_dir or self.PROFILES_DIR
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._model: Optional[XTTSAPI] = None
        self._profiles: dict[str, VoiceProfile] = {}
        self._load_profiles()

        if not XTTS_AVAILABLE:
            logger.error(
                "[VoiceCloner] XTTS não disponível!\n"
                "Instale com: pip install TTS\n"
                "Atenção: requer ~2GB de download na primeira execução."
            )

    # ─── Gerenciamento de modelo ─────────────────────────────────────

    def _load_model(self) -> bool:
        """Carrega o modelo XTTS-v2 (lazy loading — demora ~30s na primeira vez)."""
        if self._model is not None:
            return True
        if not XTTS_AVAILABLE:
            return False
        try:
            logger.info("[VoiceCloner] Carregando XTTS-v2... (pode demorar na primeira vez)")
            self._model = XTTSAPI(self.MODEL_NAME, gpu=False)
            logger.info("[VoiceCloner] XTTS-v2 carregado com sucesso!")
            return True
        except Exception as e:
            logger.error(f"[VoiceCloner] Erro ao carregar modelo: {e}")
            self._model = None
            return False

    # ─── Gerenciamento de perfis ─────────────────────────────────────

    def _load_profiles(self) -> None:
        """Carrega perfis salvos em disco."""
        index_path = self._profiles_dir / "index.json"
        if index_path.exists():
            try:
                with open(index_path, encoding="utf-8") as f:
                    data = json.load(f)
                self._profiles = {
                    pid: VoiceProfile.from_dict(pdata)
                    for pid, pdata in data.items()
                }
                logger.info(f"[VoiceCloner] {len(self._profiles)} perfis carregados")
            except Exception as e:
                logger.error(f"[VoiceCloner] Erro ao carregar perfis: {e}")

    def _save_profiles(self) -> None:
        """Salva índice de perfis em disco."""
        index_path = self._profiles_dir / "index.json"
        data = {pid: p.to_dict() for pid, p in self._profiles.items()}
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_profiles(self) -> list[VoiceProfile]:
        """Retorna todos os perfis de voz disponíveis."""
        return list(self._profiles.values())

    def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Retorna um perfil pelo ID."""
        return self._profiles.get(profile_id)

    def delete_profile(self, profile_id: str) -> bool:
        """Remove um perfil de voz."""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        # Remove pasta do perfil
        profile_dir = self._profiles_dir / profile_id
        if profile_dir.exists():
            shutil.rmtree(profile_dir)
        del self._profiles[profile_id]
        self._save_profiles()
        logger.info(f"[VoiceCloner] Perfil removido: {profile.name}")
        return True

    # ─── Pré-processamento de áudio ──────────────────────────────────

    def _convert_to_wav(self, input_path: str, output_path: str) -> bool:
        """
        Converte qualquer formato de áudio para WAV 22050Hz mono.
        Requer pydub. Se não disponível, apenas copia se já for WAV.
        """
        input_path = str(input_path)
        output_path = str(output_path)

        # Se já é WAV e pydub não está disponível, usa diretamente
        if not PYDUB_AVAILABLE:
            if input_path.lower().endswith(".wav"):
                shutil.copy(input_path, output_path)
                logger.info("[VoiceCloner] pydub não disponível, usando WAV direto")
                return True
            else:
                logger.error(
                    "[VoiceCloner] pydub não instalado. Para suportar MP3/OGG/etc, execute:\n"
                    "  pip install pydub\n"
                    "  (também requer FFmpeg instalado)"
                )
                return False

        try:
            audio = AudioSegment.from_file(input_path)
            # Normaliza: mono, 22050Hz (ideal para XTTS)
            audio = audio.set_channels(1).set_frame_rate(22050)
            audio.export(output_path, format="wav")
            return True
        except Exception as e:
            logger.error(f"[VoiceCloner] Erro na conversão de áudio: {e}")
            return False

    def _get_audio_duration(self, wav_path: str) -> float:
        """Retorna a duração em segundos de um arquivo WAV."""
        try:
            import wave
            with wave.open(wav_path, "r") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception:
            return 0.0

    def _validate_reference_audio(self, wav_path: str) -> tuple[bool, str]:
        """
        Valida se o áudio de referência é adequado para clonagem.
        Retorna (ok, mensagem).
        """
        duration = self._get_audio_duration(wav_path)

        if duration < 3.0:
            return False, f"Áudio muito curto ({duration:.1f}s). Mínimo recomendado: 6 segundos."
        if duration < 6.0:
            return True, f"⚠ Áudio curto ({duration:.1f}s). Recomendado: 6-30s para melhor qualidade."
        if duration > 30.0:
            return True, f"⚠ Áudio longo ({duration:.1f}s). XTTS usará apenas os primeiros 30s."

        return True, f"✓ Duração ideal: {duration:.1f}s"

    # ─── Criação de perfil ────────────────────────────────────────────

    async def create_profile(
        self,
        audio_path: str,
        name: str,
        language: str = "pt",
        description: str = "",
    ) -> VoiceProfile:
        """
        Cria um perfil de voz clonada a partir de um áudio de referência.

        Args:
            audio_path: Caminho para o áudio de referência (WAV, MP3, OGG, etc.)
                        Ideal: 6-30 segundos de fala limpa, sem música de fundo.
            name: Nome do perfil (ex: "Narrador", "Personagem X")
            language: Código do idioma ("pt", "en", "es", "fr", etc.)
            description: Descrição opcional do perfil

        Returns:
            VoiceProfile com os dados do perfil criado

        Raises:
            FileNotFoundError: Se o arquivo de áudio não existir
            ValueError: Se o áudio for inadequado para clonagem
            RuntimeError: Se o XTTS não estiver disponível
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")

        if not XTTS_AVAILABLE:
            raise RuntimeError(
                "XTTS não instalado. Execute: pip install TTS\n"
                "Nota: requer ~2GB de download e ~4GB de RAM."
            )

        logger.info(f"[VoiceCloner] Criando perfil '{name}' de {audio_path.name}...")

        # Cria pasta do perfil
        profile_id = str(uuid.uuid4())[:8]
        profile_dir = self._profiles_dir / profile_id
        profile_dir.mkdir(parents=True, exist_ok=True)

        # Converte para WAV
        wav_path = str(profile_dir / "reference.wav")
        ok = await asyncio.to_thread(self._convert_to_wav, str(audio_path), wav_path)
        if not ok:
            raise ValueError(f"Não foi possível converter '{audio_path}' para WAV.")

        # Valida qualidade
        valid, msg = self._validate_reference_audio(wav_path)
        if not valid:
            shutil.rmtree(profile_dir)
            raise ValueError(msg)
        if msg.startswith("⚠"):
            logger.warning(f"[VoiceCloner] {msg}")
        else:
            logger.info(f"[VoiceCloner] {msg}")

        duration = self._get_audio_duration(wav_path)

        # Cria perfil
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

        logger.info(
            f"[VoiceCloner] Perfil '{name}' criado! "
            f"ID: {profile_id} | Duração ref: {duration:.1f}s"
        )
        return profile

    # ─── Síntese com voz clonada ──────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        profile_id: str,
        speed: float = 1.0,
        temperature: float = 0.75,
    ) -> bytes:
        """
        Sintetiza texto usando uma voz clonada.

        Args:
            text: Texto para sintetizar
            profile_id: ID do perfil de voz criado com create_profile()
            speed: Velocidade da fala (0.5 = devagar, 1.0 = normal, 2.0 = rápido)
            temperature: Criatividade da voz (0.1 = conservador, 1.0 = variado)

        Returns:
            Áudio WAV em bytes

        Raises:
            KeyError: Se o profile_id não existir
            RuntimeError: Se o XTTS não estiver disponível
        """
        if not XTTS_AVAILABLE:
            raise RuntimeError("XTTS não instalado. Execute: pip install TTS")

        profile = self._profiles.get(profile_id)
        if not profile:
            raise KeyError(
                f"Perfil '{profile_id}' não encontrado. "
                f"Perfis disponíveis: {list(self._profiles.keys())}"
            )

        if not Path(profile.reference_wav).exists():
            raise FileNotFoundError(
                f"Arquivo de referência não encontrado: {profile.reference_wav}\n"
                "O perfil pode ter sido movido ou deletado."
            )

        logger.info(
            f"[VoiceCloner] Sintetizando com voz '{profile.name}' | "
            f"{len(text)} chars | lang={profile.language}"
        )

        audio_bytes = await asyncio.to_thread(
            self._synthesize_sync, text, profile, speed, temperature
        )
        return audio_bytes

    def _synthesize_sync(
        self,
        text: str,
        profile: VoiceProfile,
        speed: float,
        temperature: float,
    ) -> bytes:
        """Síntese síncrona (rodada em thread para não bloquear o event loop)."""
        if not self._load_model():
            raise RuntimeError("Não foi possível carregar o modelo XTTS.")

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

            logger.info(
                f"[VoiceCloner] Áudio gerado: {len(audio_bytes)} bytes "
                f"com voz '{profile.name}'"
            )
            return audio_bytes

        finally:
            try:
                os.unlink(output_path)
            except Exception:
                pass

    # ─── Utilitários ─────────────────────────────────────────────────

    async def synthesize_and_save(
        self,
        text: str,
        profile_id: str,
        output_path: str,
        **kwargs,
    ) -> str:
        """
        Sintetiza e salva diretamente em um arquivo.

        Returns:
            Caminho do arquivo salvo
        """
        audio_bytes = await self.synthesize(text, profile_id, **kwargs)
        output_path = str(output_path)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        logger.info(f"[VoiceCloner] Salvo em: {output_path}")
        return output_path

    def get_supported_languages(self) -> list[str]:
        """Lista os idiomas suportados pelo XTTS-v2."""
        return [
            "pt",   # Português
            "en",   # Inglês
            "es",   # Espanhol
            "fr",   # Francês
            "de",   # Alemão
            "it",   # Italiano
            "pl",   # Polonês
            "tr",   # Turco
            "ru",   # Russo
            "nl",   # Holandês
            "cs",   # Tcheco
            "ar",   # Árabe
            "zh-cn",# Chinês
            "hu",   # Húngaro
            "ko",   # Coreano
            "ja",   # Japonês
            "hi",   # Hindi
        ]

    def __repr__(self) -> str:
        return (
            f"VoiceCloner("
            f"profiles={len(self._profiles)}, "
            f"xtts_available={XTTS_AVAILABLE}, "
            f"model_loaded={self._model is not None}"
            f")"
        )
