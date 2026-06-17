"""
config/constants.py
Constantes globais do sistema. Nunca expõe segredos.
"""
from __future__ import annotations

APP_NAME = "Shaz AI"
APP_VERSION = "3.0.0"

# Limites
MAX_MESSAGE_LENGTH = 4096
MAX_MEMORY_ENTRIES = 1000
MAX_HISTORY_MESSAGES = 50
MAX_SEARCH_RESULTS = 10

# TTL de cache (segundos)
WEATHER_CACHE_TTL = 600        # 10 minutos
WIKIPEDIA_CACHE_TTL = 3600     # 1 hora
GITHUB_CACHE_TTL = 300         # 5 minutos

# Fallback chain para LLM
LLM_FALLBACK_ORDER = ["gemini", "groq", "openai", "openrouter", "ollama"]

# Categorias de memória
MEMORY_TYPES = ["fact", "preference", "knowledge", "interaction", "summary"]

# Status do sistema
STATUS_ONLINE = "online"
STATUS_PROCESSING = "processing"
STATUS_LISTENING = "listening"
STATUS_SPEAKING = "speaking"
STATUS_OFFLINE = "offline"
