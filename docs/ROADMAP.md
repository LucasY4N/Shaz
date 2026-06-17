# ROADMAP.md

## Fase 1 — Base Profissional ✅ (atual)

- [x] Arquitetura hexagonal com `core/`, `shaz/`, `providers/`
- [x] Múltiplos provedores LLM com fallback automático
- [x] Memória persistente SQLite
- [x] Personalidade e lore completa
- [x] Sistema de voz (STT + TTS + clonagem)
- [x] Interface desktop PySide6 + CLI
- [x] Servidor HTTP + WebSocket (FastAPI)
- [x] Interface web interativa (NEXUS v3.0)

## Fase 2 — Upgrade Estrutural ✅ (este upgrade)

- [x] Separação de rotas por domínio (`backend/routes/`)
- [x] Schemas Pydantic para todas as rotas
- [x] Middleware de logging HTTP
- [x] Config centralizada com pydantic-settings
- [x] Logger por módulo (`logs/logger.py`)
- [x] 5 agents com responsabilidade única
- [x] API GitHub (repos, commits, issues, PRs, users)
- [x] API Weather (OpenWeatherMap: atual + previsão)
- [x] API Tavily (pesquisa web inteligente)
- [x] API Wikipedia (resumos PT + EN com cache)
- [x] Documentação técnica completa (`docs/`)
- [x] `.env.example` atualizado com todas as chaves

## Fase 3 — Frontend React (próxima)

- [ ] Setup React + Vite + TypeScript em `frontend/`
- [ ] Dashboard com status em tempo real via WebSocket
- [ ] Tela de Chat com Markdown, code blocks e histórico
- [ ] Tela de Configurações (provedores, voz, APIs)
- [ ] Tela de Logs do sistema
- [ ] Tela de Ferramentas (clima, pesquisa, GitHub)

## Fase 4 — Memória Avançada

- [ ] ChromaDB para busca vetorial semântica
- [ ] `memory/vector_memory.py`
- [ ] Busca por similaridade (em vez de LIKE)
- [ ] Consolidação automática de memórias antigas
- [ ] Exportação e importação de memórias

## Fase 5 — Integrações

- [ ] Discord: bot com comandos e menções
- [ ] VTube Studio: avatar sincronizado com voz
- [ ] Minecraft: servidor via RCON
- [ ] MCP (Model Context Protocol): ferramentas externas
- [ ] ElevenLabs: TTS de alta qualidade

## Fase 6 — Produção

- [ ] Autenticação JWT
- [ ] Rate limiting por usuário
- [ ] Testes unitários e de integração (cobertura >80%)
- [ ] CI/CD com GitHub Actions
- [ ] Build executável Windows (.exe) atualizado
