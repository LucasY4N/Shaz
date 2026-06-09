"""
PATCH para shaz/voice/tts.py — adiciona suporte a voz clonada no TTSManager.

Cole este trecho no final da classe TTSManager (no arquivo shaz/voice/tts.py),
ou use esta classe estendida diretamente.

Adiciona o método synthesize_cloned() e a engine "cloned" na cadeia de fallback.
"""

# ─── Exemplo de uso integrado ─────────────────────────────────────────────
#
# from shaz.voice.tts import TTSManager
# from shaz.voice.voice_cloner import VoiceCloner
#
# # Clonar uma voz
# cloner = VoiceCloner()
# profile = await cloner.create_profile("referencia.wav", "Narrador", language="pt")
#
# # Gerar com voz clonada
# audio = await cloner.synthesize("Olá! Estou testando a clonagem.", profile.id)
#
# # Reproduzir
# manager = TTSManager()
# manager._audio.player.play_bytes(audio)  # se tiver AudioManager
# ─────────────────────────────────────────────────────────────────────────

TTSMANAGER_PATCH = '''
    # ─── Integração com Voice Cloner ──────────────────────────────────────────

    async def synthesize_cloned(
        self,
        text: str,
        profile_id: str,
        speed: float = 1.0,
        temperature: float = 0.75,
    ) -> Optional[bytes]:
        """
        Sintetiza texto usando uma voz clonada.
        Wrapper conveniente para VoiceCloner.

        Args:
            text: Texto para sintetizar
            profile_id: ID do perfil de voz (gerado com VoiceCloner.create_profile)
            speed: Velocidade da fala (padrão: 1.0)
            temperature: Variação da voz (padrão: 0.75)

        Returns:
            Áudio WAV em bytes ou None em caso de falha

        Exemplo:
            # 1. Criar perfil
            from shaz.voice.voice_cloner import VoiceCloner
            cloner = VoiceCloner()
            profile = await cloner.create_profile("voz.wav", "Minha Voz")

            # 2. Usar pelo TTSManager
            audio = await tts_manager.synthesize_cloned("Olá!", profile.id)
        """
        try:
            from shaz.voice.voice_cloner import VoiceCloner
            cloner = VoiceCloner()
            audio = await cloner.synthesize(text, profile_id, speed, temperature)
            logger.tts(f"Cloned voice synthesized: {len(audio)} bytes")
            return audio
        except Exception as e:
            logger.error(f"[TTS] Cloned voice error: {e}")
            return None

    async def list_cloned_voices(self):
        """Lista todas as vozes clonadas disponíveis."""
        try:
            from shaz.voice.voice_cloner import VoiceCloner
            cloner = VoiceCloner()
            return cloner.list_profiles()
        except Exception:
            return []
'''

# ─── Exemplo de uso standalone ────────────────────────────────────────────

USAGE_EXAMPLE = """
# ============================================================
# COMO USAR — Clonagem de Voz no Shaz AI
# ============================================================

# PASSO 1: Instalar dependências
# pip install TTS              ← modelo XTTS-v2 (~2GB, faz offline)
# pip install pydub            ← para converter MP3/OGG para WAV (opcional)
# (FFmpeg também é necessário para pydub: https://ffmpeg.org)

# PASSO 2: Gravar ou obter um áudio de referência
# - Grave ~10-20 segundos da voz que deseja clonar
# - O áudio deve ser limpo (sem ruído de fundo ou música)
# - Formatos aceitos: WAV, MP3, OGG, FLAC
# - Salve como: minha_voz.wav (ou MP3)

# PASSO 3: Criar o perfil de voz
python clone_voice.py clonar --audio minha_voz.wav --nome "Lucas" --lang pt

# Saída esperada:
# ✓ Perfil criado com sucesso!
#   Nome:     Lucas
#   ID:       a1b2c3d4
#   Duração:  15.3s

# PASSO 4: Gerar mensagens com a voz clonada
python clone_voice.py gerar --perfil a1b2c3d4 --texto "Olá! Esta é minha voz clonada." --saida saida.wav

# Com reprodução automática:
python clone_voice.py gerar --perfil a1b2c3d4 --texto "Testando!" --saida saida.wav --reproduzir

# PASSO 5 (opcional): Ver todos os perfis salvos
python clone_voice.py listar

# PASSO 6 (opcional): Integrar no código Python
from shaz.voice.voice_cloner import VoiceCloner
import asyncio

async def exemplo():
    cloner = VoiceCloner()
    
    # Criar perfil
    profile = await cloner.create_profile(
        audio_path="minha_voz.wav",
        name="Lucas",
        language="pt"
    )
    print(f"Perfil criado: {profile.id}")
    
    # Gerar mensagem
    audio_bytes = await cloner.synthesize(
        text="Olá! Minha voz foi clonada pela Shaz AI.",
        profile_id=profile.id
    )
    
    # Salvar
    with open("resultado.wav", "wb") as f:
        f.write(audio_bytes)
    print("Salvo em resultado.wav!")

asyncio.run(exemplo())
"""

if __name__ == "__main__":
    print(USAGE_EXAMPLE)
