# ⚡ Shaz AI

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

**Shaz AI** é um assistente inteligente com **arquitetura hexagonal** (ports & adapters), suporte a múltiplos provedores de LLM (Gemini, Groq), memória persistente com MongoDB, voz (STT/TTS), geração de imagens e aprendizado contínuo via YouTube.

---

## ✨ Funcionalidades

| Funcionalidade | Status | Descrição |
|----------------|--------|-----------|
| 💬 **Chat inteligente** | ✅ | Gemini 2.5 Flash / Groq com histórico |
| 🧠 **Memória persistente** | ✅ | Curto/longo prazo, preferências, conhecimento |
| 🎙️ **Voz (STT → IA → TTS)** | ✅ | Google STT + pyttsx3 / gTTS / ElevenLabs |
| 🎨 **Geração de imagens** | ✅ | Local (SD) / Replicate / Stability AI |
| 📚 **YouTube Learning** | ✅ | Transcrição → resumo → flashcards |
| 🩺 **Diagnóstico de código** | ✅ | Analisa erros e sugere correções |
| 📊 **Dashboard terminal** | ✅ | CPU, RAM, MongoDB, logs em tempo real |
| 🔌 **Discord** | 🔜 | Gateway preparado |

---

## 🚀 Como usar

### 1. Clonar e configurar

```bash
git clone https://github.com/LucasY4N/Shaz.git
cd shaz_ai

# Configurar ambiente
cp .env.example .env
# Edite .env com suas chaves (veja seção abaixo)
```

### 2. Instalar dependências

```bash
# Windows (recomendado — instala tudo inclusive pyaudio)
install_windows.bat

# OU manual
pip install -e ".[dev]"
```

### 3. Subir MongoDB

```bash
docker run -d -p 27017:27017 --name shaz-mongo mongo:7
```

### 4. Rodar!

```bash
# Modo chat
python main.py chat "Olá, quem é você?"

# Diagnóstico de erro
python main.py diagnose "TypeError: 'NoneType' is not subscriptable"

# Aprender com vídeo do YouTube
python main.py learn https://www.youtube.com/watch?v=SEU_VIDEO

# Dashboard
python main.py dashboard

# Modo voz (requer pyaudio)
python main.py voice
```

---

## 🔑 Variáveis de Ambiente

| Variável | Obrigatório | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `MONGODB_URI` | ✅ | `mongodb://localhost:27017` | URI do MongoDB |
| `MONGODB_DB` | — | `shaz_ai` | Nome do banco |
| `GEMINI_API_KEY` | ✅* | — | Chave da API Google Gemini |
| `GEMINI_MODEL` | — | `gemini-2.5-flash` | Modelo Gemini |
| `GROQ_API_KEY` | ✅* | — | Chave da API Groq (alternativa) |
| `LOG_LEVEL` | — | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENVIRONMENT` | — | `development` | `development` ou `production` |

> *`GEMINI_API_KEY` ou `GROQ_API_KEY` é obrigatório.

---

## 🏗️ Arquitetura

```
shaz_ai/
├── core/                   # Domínio puro (zero dependências externas)
│   ├── entities/           # Message, Memory, Conversation...
│   ├── ports/              # Interfaces: LLMPort, MemoryPort...
│   └── use_cases/          # Chat, ProgrammingAssistant, YouTubeLearning
│
├── providers/              # Adaptadores de infraestrutura
│   ├── llm/               # Gemini (google.genai), Groq
│   ├── voice/             # STT (Google), TTS (pyttsx3)
│   └── image/             # Geração de imagens
│
├── repositories/           # MongoDB (motor async com motor)
├── infrastructure/         # Config, Logging (loguru), Security
├── services/               # Container DI (injeção de dependências)
├── integrations/           # YouTube, Discord (futuro)
├── dashboard/              # Terminal dashboard com Rich
└── tests/                  # Pytest com mocks
```

### 🧱 Princípios

- **Arquitetura Hexagonal** — domínio isolado de infraestrutura
- **Ports & Adapters** — interfaces no `core/ports/`, implementações em `providers/`
- **Injeção de Dependências** — container em `services/container.py`
- **Async/await** — operações não-bloqueantes com `asyncio`

---

## 🛠️ Dev Tools

```bash
ruff check .                # Linting
black .                     # Formatação
mypy .                      # Type checking
pytest -v                   # Testes
pre-commit install          # Hooks automáticos
```

---

## 📦 Stack

| Categoria | Tecnologia |
|-----------|------------|
| **Linguagem** | Python 3.11+ |
| **LLM** | Google Gemini (`google-genai`), Groq |
| **Banco** | MongoDB (`motor` async) |
| **CLI** | Typer + Rich |
| **Voz** | Google Speech Recognition, pyttsx3, gTTS, ElevenLabs |
| **Imagens** | Stable Diffusion (local), Replicate, Stability AI |
| **Vídeo** | yt-dlp + YouTube Transcript API |
| **Segurança** | python-dotenv, pydantic-settings |
| **Qualidade** | Ruff, Black, mypy, pytest |

---

## 📄 Licença

Distribuído sob licença **MIT**. Veja [LICENSE](LICENSE) para mais informações.

---

<p align="center">
  Feito com ☕ por <a href="https://github.com/LucasY4N">LucasY4N</a>
</p>