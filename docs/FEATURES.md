# FEATURES.md

## Funcionalidades Implementadas

### Core
| Funcionalidade | Status | Módulo |
|---|---|---|
| Chat com LLM (Gemini/Groq/OpenAI/Ollama) | ✅ | `shaz/core/brain.py` |
| Fallback automático entre provedores | ✅ | `shaz/services/api_manager.py` |
| Memória persistente SQLite | ✅ | `shaz/core/memory.py` |
| Personalidade e lore (Pyxis-7) | ✅ | `shaz/core/personality.py` |
| Extração automática de preferências | ✅ | `agents/memory_agent.py` |

### Voz
| Funcionalidade | Status | Módulo |
|---|---|---|
| STT com Faster-Whisper | ✅ | `shaz/voice/stt.py` |
| TTS com Edge TTS | ✅ | `shaz/voice/tts.py` |
| TTS com XTTS-v2 (clonagem) | ✅ | `shaz/voice_cloner.py` |
| TTS com Piper (local) | ✅ | `shaz/voice/tts.py` |
| Loop de voz contínuo (ouve → fala) | ✅ | `shaz/core/brain.py` |
| Fila de fala assíncrona | ✅ | `shaz/core/brain.py` |
| Suporte a VoiceMeeter | ✅ | `shaz/voice/audio_voicemeeter.py` |

### Interfaces
| Funcionalidade | Status | Módulo |
|---|---|---|
| Dashboard desktop (PySide6) | ✅ | `shaz/ui/dashboard.py` |
| Chat com bolhas (PySide6) | ✅ | `shaz/ui/chat.py` |
| Terminal de logs em tempo real | ✅ | `shaz/ui/terminal.py` |
| Interface web HTML (NEXUS v3.0) | ✅ | `shaz-terminal.html` |
| Modo CLI interativo | ✅ | `shaz/main.py` |
| Servidor HTTP + WebSocket | ✅ | `backend/main.py` |

### APIs Externas (novo)
| Funcionalidade | Status | Módulo | Chave necessária |
|---|---|---|---|
| Clima atual e previsão | ✅ | `apis/weather/` | `OPENWEATHER_API_KEY` |
| Pesquisa web (Tavily) | ✅ | `apis/tavily/` | `TAVILY_API_KEY` |
| Wikipedia (PT + EN) | ✅ | `apis/wikipedia/` | Nenhuma |
| Análise de repositório GitHub | ✅ | `apis/github/` | `GITHUB_TOKEN` |
| Commits, issues, PRs do GitHub | ✅ | `apis/github/` | `GITHUB_TOKEN` |

### Agents (novo)
| Agente | Status | Responsabilidade |
|---|---|---|
| `ChatAgent` | ✅ | Orquestra conversa principal |
| `CodingAgent` | ✅ | Diagnóstico de erros, code review, explicação |
| `ResearchAgent` | ✅ | Pesquisa com Tavily + Wikipedia + GitHub |
| `MemoryAgent` | ✅ | Extração e recuperação de memórias |
| `SystemAgent` | ✅ | Monitoramento de CPU, RAM, serviços |

### Backend Refatorado (novo)
| Funcionalidade | Status | Módulo |
|---|---|---|
| Rotas separadas por domínio | ✅ | `backend/routes/` |
| Schemas Pydantic validados | ✅ | `backend/schemas/` |
| Middleware de logging HTTP | ✅ | `backend/middlewares/` |
| Config centralizada via .env | ✅ | `config/settings.py` |
| Logger por módulo | ✅ | `logs/logger.py` |

---

## Em Desenvolvimento (SOON)

| Funcionalidade | Módulo planejado |
|---|---|
| Frontend React + Vite + TypeScript | `frontend/` |
| Integração Discord | `integrations/discord/` |
| VTube Studio (avatar sincronizado) | `integrations/vtube/` |
| Servidor Minecraft via RCON | `integrations/minecraft/` |
| MCP (Model Context Protocol) | `integrations/mcp/` |
| Memória vetorial (ChromaDB) | `memory/vector_memory.py` |
| Autenticação de usuários | `backend/dependencies/auth.py` |
| Testes unitários e de integração | `tests/` |
