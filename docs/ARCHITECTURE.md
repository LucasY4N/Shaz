# ARCHITECTURE.md

## Visão Geral

Shaz AI é organizado em camadas isoladas com responsabilidades únicas. Cada camada só conhece a camada abaixo dela.

```
UI (React / Terminal HTML)
        ↓
Backend (FastAPI) — apenas roteamento e validação
        ↓
Agents — orquestração de fluxos
        ↓
Services — lógica de negócio
        ↓
APIs externas / Memory / Voice / Database
        ↓
Brain (legado, mantido compatível)
```

---

## Estrutura de Pastas

```
shaz_ai/
├── backend/                    # Servidor FastAPI
│   ├── main.py                 # App, lifecycle, WebSocket
│   ├── routes/                 # Uma rota por domínio
│   │   ├── chat.py             # POST /api/chat
│   │   ├── voice.py            # POST /api/voice/*
│   │   ├── tools.py            # POST /api/tools/*
│   │   └── stats.py            # GET /api/stats, /api/stats/status
│   ├── middlewares/            # Logging, CORS, auth
│   ├── schemas/                # Pydantic: requests.py, responses.py
│   └── dependencies/           # Injeção de dependências FastAPI
│
├── apis/                       # Integrações externas (1 pasta = 1 API)
│   ├── gemini/                 # client.py, service.py, models.py
│   ├── groq/
│   ├── ollama/
│   ├── github/                 # Repos, commits, issues, PRs, users
│   ├── weather/                # OpenWeatherMap: clima atual + previsão
│   ├── tavily/                 # Busca web inteligente
│   └── wikipedia/              # Resumos e busca de artigos
│
├── agents/                     # Um agente = uma responsabilidade
│   ├── chat_agent.py           # Conversa principal
│   ├── coding_agent.py         # Debugging, code review, diagnóstico
│   ├── research_agent.py       # Pesquisa com Tavily + Wikipedia + GitHub
│   ├── memory_agent.py         # Extração e recuperação de memórias
│   └── system_agent.py         # Status, CPU, RAM, serviços
│
├── services/                   # Orquestração entre módulos
├── memory/                     # Sistema de memória (futura separação)
├── voice/                      # STT, TTS, processamento de áudio
│   ├── speech_to_text/
│   ├── text_to_speech/
│   └── audio_processing/
├── database/                   # Persistência
│   └── repositories/
│
├── config/
│   ├── settings.py             # Pydantic-settings, lê .env
│   └── constants.py            # Constantes globais
│
├── logs/
│   └── logger.py               # Logger centralizado por módulo
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── docs/                       # Esta documentação
└── shaz/ (legado)              # Brain, Memory, Personality — mantidos
```

---

## Princípios de Design

### 1. Uma responsabilidade por módulo
- Rotas não têm lógica de negócio
- Agentes não acessam banco diretamente
- APIs externas não sabem nada sobre o domínio

### 2. Injeção de dependências via `_state`
O dicionário `_state` em `backend/main.py` é o container de dependências. Cada rota recebe o que precisa via closure no `register(app_state)`.

### 3. Compatibilidade com o legado
O `ShazBrain` em `shaz/core/brain.py` é preservado. O novo backend inicializa e usa o Brain sem reescrever nada que já funciona.

### 4. APIs externas isoladas
Cada API tem: `client.py` (HTTP puro), `models.py` (dataclasses), `service.py` (lógica). Nenhuma depende de outra.

---

## Fluxo de uma Mensagem de Chat

```
1. POST /api/chat {message: "Olá!"}
2. ChatRoute → valida com Pydantic (ChatRequest)
3. ChatRoute → chama brain.process_message(message)
4. Brain → busca histórico + memórias (SQLite)
5. Brain → monta system_prompt com Personality
6. Brain → chama APIManager (Gemini/Groq/Ollama com fallback)
7. Brain → salva resposta na memória
8. Brain → MemoryAgent extrai preferências implícitas
9. ChatRoute → retorna ChatResponse {response, tokens, provider}
```

---

## Fluxo de Pesquisa com Ferramentas

```
1. POST /api/tools/search {query: "..."}
2. ToolsRoute → chama TavilyService.search(query)
3. TavilyService → chama TavilyClient.search() [HTTP]
4. TavilyService → retorna SearchResponse estruturado
5. ToolsRoute → retorna ActionResponse {status, data}
```

---

## WebSocket

Evento `exec`: executa comandos seguros (allowlist) no terminal do dashboard.
Evento `chat`: processa mensagem e retorna resposta.
Evento `status`: broadcast de mudanças de estado do Brain.
