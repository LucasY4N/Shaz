# API_LIST.md

## Base URL
`http://localhost:8765`

Documentação interativa: `GET /docs` (Swagger) ou `GET /redoc`

---

## Chat

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/chat` | Envia mensagem, recebe resposta da Shaz |
| `POST` | `/api/chat/clear` | Limpa histórico de conversa |

**POST /api/chat**
```json
// Request
{ "message": "Olá Shaz!" }

// Response
{ "response": "Olá! Como posso ajudar?", "tokens": 42, "provider": "gemini" }
```

---

## Estatísticas

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/stats` | Mensagens, tokens, memórias, provedor |
| `GET` | `/api/stats/status` | Status completo: serviços, voz, providers |

---

## Voz

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/voice/start` | Ativa modo de voz (STT + TTS em loop) |
| `POST` | `/api/voice/stop` | Desativa modo de voz |
| `POST` | `/api/voice/stop_speaking` | Interrompe a fala atual |
| `POST` | `/api/voice/test` | Testa TTS com frase padrão |
| `POST` | `/api/voice/set` | Troca voz Edge TTS |
| `POST` | `/api/voice/engine` | Troca engine TTS (edge/piper/xtts) |
| `GET`  | `/api/voice/status` | `{ "voice_active": bool }` |

**POST /api/voice/set**
```json
{ "voice": "pt-BR-FranciscaNeural" }
```

**POST /api/voice/engine**
```json
{ "engine": "edge" }
```

---

## Ferramentas Externas

| Método | Endpoint | Requer | Descrição |
|--------|----------|--------|-----------|
| `POST` | `/api/tools/weather` | `OPENWEATHER_API_KEY` | Clima atual de uma cidade |
| `POST` | `/api/tools/search` | `TAVILY_API_KEY` | Pesquisa web inteligente |
| `POST` | `/api/tools/wikipedia` | — | Resumo do Wikipedia |
| `POST` | `/api/tools/github/repo` | `GITHUB_TOKEN` | Análise de repositório GitHub |
| `POST` | `/api/tools/diagnose` | LLM | Diagnóstico de erro de código |

**POST /api/tools/weather**
```json
// Request
{ "city": "Manaus" }

// Response
{
  "status": "ok",
  "data": {
    "city": "Manaus", "country": "BR",
    "temperature": 32.1, "feels_like": 38.5,
    "humidity": 85, "description": "chuva moderada",
    "wind_speed": 2.1,
    "text": "Clima em Manaus, BR: Chuva moderada, 32.1°C..."
  }
}
```

**POST /api/tools/search**
```json
// Request
{ "query": "Python asyncio 2025", "max_results": 5 }

// Response
{
  "status": "ok",
  "data": {
    "query": "...", "answer": "Resposta direta...",
    "context": "## Pesquisa Web\n...",
    "results": [{ "title": "...", "url": "...", "snippet": "..." }]
  }
}
```

**POST /api/tools/github/repo**
```json
// Request
{ "owner": "anthropics", "repo": "anthropic-sdk-python" }

// Response
{
  "status": "ok",
  "data": {
    "repository": { "name": "...", "stars": 1200, "language": "Python", ... },
    "recent_commits": [{ "sha": "abc1234", "message": "...", "author": "..." }],
    "open_issues": [{ "number": 42, "title": "...", "state": "open" }]
  }
}
```

**POST /api/tools/diagnose**
```json
// Request
{ "error": "TypeError: 'NoneType' is not subscriptable", "code": "x = None\nprint(x[0])", "language": "python" }

// Response
{
  "status": "ok",
  "data": {
    "error_type": "TypeError",
    "root_cause": "A variável x é None e não pode ser indexada.",
    "patch": "if x is not None:\n    print(x[0])",
    "explanation": "...",
    "references": []
  }
}
```

---

## WebSocket

`ws://localhost:8765/ws`

### Eventos enviados pelo cliente

```json
{ "type": "chat", "message": "Olá!" }
{ "type": "ping" }
{ "type": "exec", "cmd": "python --version" }
```

### Eventos recebidos do servidor

```json
{ "type": "connected", "message": "Shaz AI 3.0.0 — conectado" }
{ "type": "response", "response": "Olá! Como posso ajudar?" }
{ "type": "status", "status": "processing" }
{ "type": "pong" }
{ "type": "terminal_out", "text": "Python 3.11.9" }
{ "type": "terminal_err", "text": "Comando não permitido: rm -rf /" }
{ "type": "terminal_done" }
```

---

## Páginas HTML

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/` | Status JSON da API |
| `GET` | `/app` | Interface web (shaz-terminal.html) |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |
