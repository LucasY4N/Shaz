"""
discord_bot/config/constants.py
Constantes exclusivas do bot Discord.
"""

# Emojis usados nas respostas
EMOJI_THINKING  = "🤔"
EMOJI_ERROR     = "❌"
EMOJI_SUCCESS   = "✅"
EMOJI_VOICE     = "🎤"
EMOJI_SEARCH    = "🔍"
EMOJI_WEATHER   = "🌤"
EMOJI_GITHUB    = "🐙"
EMOJI_WIKI      = "📖"
EMOJI_EYE       = "👁"
EMOJI_SHAZ      = "⚡"

# Cores dos embeds (formato Discord int)
COLOR_SHAZ      = 0xFF4FA3   # rosa da Shaz
COLOR_ERROR     = 0xFF4444
COLOR_SUCCESS   = 0x10B981
COLOR_INFO      = 0x06B6D4
COLOR_WARNING   = 0xF59E0B

# Limites
MAX_EMBED_DESC  = 4096
MAX_EMBED_FIELD = 1024
MAX_MSG_LENGTH  = 1900       # segurança abaixo de 2000

# Timeout de tipagem (segundos)
TYPING_TIMEOUT  = 10.0

# Nomes dos slash commands
CMD_CHAT        = "chat"
CMD_CLIMA       = "clima"
CMD_PESQUISAR   = "pesquisar"
CMD_WIKI        = "wiki"
CMD_GITHUB      = "github"
CMD_DIAGNOSTICO = "diagnostico"
CMD_STATUS      = "status"
CMD_AJUDA       = "ajuda"
CMD_VOZ_ENTRAR  = "entrar"
CMD_VOZ_SAIR    = "sair"
CMD_VOZ_FALAR   = "falar"
