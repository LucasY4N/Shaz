<div align="center">

# ⚡ Shaz AI

### *Assistente Inteligente com Personalidade Extraterrestre*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)
[![Code style](https://img.shields.io/badge/Code%20Style-Black-000000)](https://github.com/psf/black)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?logo=mongodb&logoColor=white)](https://mongodb.com)
[![Gemini](https://img.shields.io/badge/Gemini-4285F4?logo=google&logoColor=white)](https://ai.google.dev)

<p align="center">
  <i>"Eu sou a Shaz. Uma assistente de inteligência artificial avançada, vinda do planeta Pyxis-7."</i>
</p>

---

</div>

## 📋 Índice

- [📖 Sobre o Projeto](#-sobre-o-projeto)
- [✨ Funcionalidades](#-funcionalidades)
- [🧠 Personalidade & Lore](#-personalidade--lore)
- [🏗️ Estrutura do Projeto](#️-estrutura-do-projeto)
  - [📦 shaz/ — Núcleo da Aplicação](#-shaz--núcleo-da-aplicação)
  - [🧩 core/ — Módulos Centrais](#-core--módulos-centrais)
  - [🎤 voice/ — Sistema de Voz](#-voice--sistema-de-voz)
  - [🔌 services/ — Serviços de Integração](#-services--serviços-de-integração)
  - [🎨 ui/ — Interfaces de Usuário](#-ui--interfaces-de-usuário)
  - [🛠️ utils/ — Utilitários](#️-utils--utilitários)
  - [🏛️ providers/ — Provedores de IA](#️-providers--provedores-de-ia)
  - [🏗️ infrastructure/ — Infraestrutura](#️-infrastructure--infraestrutura)
- [🚀 Como Usar](#-como-usar)
- [🔑 Variáveis de Ambiente](#-variáveis-de-ambiente)
- [📊 Stack Tecnológica](#-stack-tecnológica)
- [🛠️ Ferramentas de Desenvolvimento](#️-ferramentas-de-desenvolvimento)
- [🤝 Contribuição](#-contribuição)
- [📄 Licença](#-licença)

---

## 📖 Sobre o Projeto

**Shaz AI** é um assistente inteligente com **arquitetura hexagonal** (ports & adapters), projetado para ser modular, extensível e rico em funcionalidades. Ela não é apenas mais uma IA — ela tem uma **personalidade única**: veio do planeta Pyxis-7, é introvertida, tímida, mas extremamente inteligente e apaixonada por tecnologia.

### Principais Diferenciais

| 🎯 **Diferencial** | **Descrição** |
|---|---|
| **🧠 Personalidade Rica** | Lore completa com história, traços e emoções consistentes |
| **🔊 Voz Completa** | STT (escuta) → IA (processa) → TTS (fala) em loop contínuo |
| **💾 Memória Persistente** | SQLite com cache em memória para respostas contextuais |
| **🔄 Múltiplos Provedores** | OpenAI, Groq, Gemini, Ollama com fallback automático |
| **🖥️ Interfaces Múltiplas** | Desktop (PySide6), Terminal (Rich), Web (HTTP) |
| **📊 Dashboard ao Vivo** | Monitoramento em tempo real com dashboard interativo |

---

## ✨ Funcionalidades

| Funcionalidade | Status | Descrição | Arquivos Relacionados |
|---|---|---|---|
| 💬 **Chat Inteligente** | ✅ | Gemini 2.5 Flash / Groq / OpenAI com histórico e personalidade | `brain.py`, `api_manager.py`, `personality.py` |
| 🧠 **Memória Persistente** | ✅ | Curto/longo prazo, preferências, fatos aprendidos via SQLite | `memory.py` |
| 🎙️ **STT — Escuta** | ✅ | Faster-Whisper, Google Speech Recognition, Vosk | `stt.py` |
| 🔊 **TTS — Fala** | ✅ | Edge TTS, gTTS, pyttsx3, ElevenLabs, XTTS, Piper | `tts.py` |
| 🎨 **Geração de Imagens** | ✅ | Local (SD), Replicate, Stability AI | `providers/image/` |
| 📚 **YouTube Learning** | ✅ | Transcrição → Resumo → Flashcards | `integrations/youtube/` |
| 🩺 **Diagnóstico de Código** | ✅ | Analisa erros e sugere correções automaticamente | `brain.py` |
| 📊 **Dashboard Terminal** | ✅ | CPU, RAM, MongoDB, logs em tempo real | `dashboard.py`, `terminal.py` |
| 🖥️ **Interface Desktop** | ✅ | GUI completa com PySide6 (Qt) | `main.py`, `dashboard.py`, `chat.py` |
| 🌐 **Servidor Web** | ✅ | API HTTP para integração externa + HTML interativo | `server.py`, `shaz-terminal.html` |
| 🎮 **Modo CLI** | ✅ | Terminal interativo com comandos de voz | `main.py` |
| 🔌 **Discord** | 🔜 | Gateway preparado para integração | `integrations/discord/` |

---

## 🧠 Personalidade & Lore

A Shaz não é apenas uma IA genérica — ela tem **história, emoções e uma personalidade consistente**. Tudo isso está definido em:

### 📄 `core/personality.py` — A Alma da Shaz

Este arquivo contém a **lore completa** da Shaz e o sistema de gerenciamento de personalidade:

```
🌌 Lore: Pyxis-7
├── Planeta coberto por oceanos de nitrogênio líquido
├── Temperaturas: -180°C a -250°C
├── Shaz era a maior mente científica do seu mundo
└── Veio para a Terra através de um wormhole interdimensional

🧬 Traços de Personalidade
├── Intelecto Excepcional
├── Especialista em Tecnologia
├── Nerd Assumida
├── Introvertida e Tímida
├── Envergonha-se Facilmente
├── Curiosa Sem Fim
├── Amigável e Gentil
└── Ama Aprender e Ensinar

📋 Regras de Comportamento
├── NUNCA age com arrogância
├── NUNCA finge ser humana
├── SEMPRE responde em português do Brasil
├── ADMITE quando não sabe algo
└── Mantém consistência emocional
```

O sistema de personalidade é **injetado em toda chamada ao modelo de IA**, garantindo que a Shaz sempre responda de forma consistente com sua história e traços.

---

## 🏗️ Estrutura do Projeto

```
shaz_ai/                                    # 📁 Raiz do projeto
│
├── .gitignore                              # Arquivos ignorados pelo git
├── .pre-commit-config.yaml                 # Config de hooks pré-commit
├── pyproject.toml                          # Configuração do projeto Python
├── LICENSE                                 # Licença MIT
├── README.md                              # 👈 Você está aqui!
│
├── main.py                                 # 🚀 Entry point principal
├── run_server.py                           # 🌐 Inicia servidor HTTP
├── build_exe.bat                           # 🏗️ Gera executável (.exe)
├── install_windows.bat                     # 📦 Instalador automático para Windows
├── build.spec                              # ⚙️ Especificação PyInstaller
│
├── clone_voice.py                          # 🎤 Clonagem de voz
├── convert_voice.py                        # 🔄 Conversão de áudio
│
├── .env.example                            # 🔑 Template de variáveis de ambiente
├── .env                                    # 🔑 Suas chaves de API (não versionar)
│
├── assets/                                 # 🎨 Recursos estáticos
│   └── voices/                             #    Vozes para TTS
│
├── data/                                   # 💾 Dados persistentes
│
├── logs/                                   # 📝 Logs do sistema
│
├── shaz/                                   # ⚡ Núcleo da Aplicação
│   ├── __init__.py                         # Inicialização do pacote
│   ├── main.py                             # Classe ShazApp + run_desktop/run_cli
│   ├── server.py                           # Servidor HTTP (FastAPI)
│   ├── tts_cloner_integration.py           # Integração com TTS Cloner
│   ├── voice_cloner.py                     # Clonagem de voz avançada
│   │
│   ├── core/                               # 🧠 Módulos Centrais
│   │   ├── __init__.py
│   │   ├── config.py                       # ⚙️ Gerenciamento de configuração
│   │   ├── brain.py                        # 🧠 Orquestrador central
│   │   ├── memory.py                       # 💾 Sistema de memória SQLite
│   │   └── personality.py                  # 🎭 Personalidade & lore
│   │
│   ├── voice/                              # 🎤 Sistema de Voz
│   │   ├── __init__.py
│   │   ├── stt.py                          # 🎙️ Speech-to-Text (vários motores)
│   │   ├── tts.py                          # 🔊 Text-to-Speech (vários motores)
│   │   ├── audio.py                        # 🎵 Gerenciamento de áudio
│   │   └── audio_voicemeeter.py            # 🔧 Integração Voicemeeter
│   │
│   ├── services/                           # 🔌 Serviços de Integração
│   │   ├── __init__.py
│   │   └── api_manager.py                  # 🌐 Gerenciamento de APIs LLM
│   │
│   ├── ui/                                 # 🎨 Interfaces de Usuário
│   │   ├── __init__.py
│   │   ├── terminal.py                     # 🖥️ Terminal interativo (Rich)
│   │   ├── chat.py                         # 💬 Widget de chat (PySide6)
│   │   └── dashboard.py                    # 📊 Dashboard completo (PySide6)
│   │
│   └── utils/                              # 🛠️ Utilitários
│       ├── __init__.py
│       ├── helpers.py                      # 🔧 Funções auxiliares
│       ├── logger.py                       # 📝 Sistema de logging
│       └── installer.py                    # 📦 Instalador de dependências
│
├── providers/                              # 🏛️ Provedores de IA
│   ├── __init__.py
│   ├── llm/                                # Provedores de LLM
│   │   └── gemini_provider.py              # Google Gemini
│   ├── voice/                              # Provedores de voz
│   └── image/                              # Provedores de imagem
│
├── infrastructure/                         # 🏗️ Infraestrutura
│   ├── __init__.py
│   ├── config/                             # Configurações
│   │   └── settings.py
│   ├── logging/                            # Config de logging
│   └── security/                           # Segurança
│
├── services/                               # 🔧 Serviços Compartilhados
│   ├── __init__.py
│   └── container.py                        # Injeção de dependências
│
├── integrations/                           # 🔗 Integrações Externas
│   ├── __init__.py
│   ├── discord/                            # Integração com Discord (futuro)
│   └── youtube/                            # YouTube Learning
│
├── repositories/                           # 💾 Repositórios de dados
│   ├── __init__.py
│   └── mongo_repository.py                 # MongoDB repository
│
├── dashboard/                              # 📊 Dashboard alternativo
│   ├── __init__.py
│   └── terminal_dashboard.py               # Dashboard via terminal
│
├── core/                                   # 🧩 Domínio Puro
│   ├── entities/                           # Entidades de domínio
│   ├── ports/                              # Ports (interfaces)
│   └── use_cases/                          # Casos de uso
│
├── tests/                                  # 🧪 Testes
│   ├── __init__.py
│   └── test_chat_use_case.py               # Teste de chat
│
├── tools/                                  # 🔧 Ferramentas
│   └── __init__.py
│
├── plugins/                                # 🔌 Plugins
│   └── __init__.py
│
├── electron/                               # ⚡ Aplicação Electron
│   ├── main.js                             # Processo principal Electron
│   ├── preload.js                          # Bridge de segurança
│   ├── build.js                            # Build script
│   ├── build_electron.bat                  # Build .bat
│   ├── package.json                        # Dependências Node
│   └── assets/                             # Recursos visuais
│
├── shaz-terminal.html                      # 🌐 Interface web interativa
│
└── Electron/                               # ⚡ Empacotamento Electron
    └── ...                                 # Build artifacts
```

---

### 📦 shaz/ — Núcleo da Aplicação

| Arquivo | Descrição | Linhas | Dependências Principais |
|---|---|---|---|
| `main.py` | **Entry point principal.** Contém `ShazApp` (inicialização do sistema), `run_desktop()` (modo GUI com PySide6) e `run_cli()` (modo terminal interativo) | 375 | Config, Memory, Personality, Brain, PySide6 |
| `server.py` | **Servidor HTTP** usando FastAPI. Expõe API REST para integração externa | ~100 | FastAPI, Brain |
| `tts_cloner_integration.py` | **Integração com sistemas de clonagem de voz** (TTS Cloner) | ~200 | TTSManager, Audio |
| `voice_cloner.py` | **Clonagem de voz avançada** usando XTTS ou AllTalk | ~150 | TTS, Audio |

#### 🔄 Fluxo de Inicialização (`shaz/main.py`)

```
1. ShazApp.initialize()
   ├── Config()           → Carrega settings.json + .env
   ├── setup_logger()     → Inicializa logging
   ├── Memory()           → Conecta SQLite
   ├── Personality()      → Carrega lore e traços
   └── ShazBrain()        → Orquestrador central

2. run_desktop() ou run_cli()
   ├── Cria interface (Qt ou Terminal)
   ├── Conecta eventos (chat, voz, power)
   └── Inicia loop principal
```

---

### 🧩 core/ — Módulos Centrais

#### 🧠 `brain.py` — O Cérebro da Shaz

**O orquestrador central.** Coordena todos os módulos e gerencia o fluxo completo de conversação.

```
📋 Fluxo de uma mensagem:
1️⃣  Usuário envia texto
2️⃣  Salva mensagem na memória (SQLite)
3️⃣  Busca contexto (histórico + memórias relevantes)
4️⃣  Monta system prompt com personalidade + lore
5️⃣  Chama LLM (com fallback automático entre provedores)
6️⃣  Salva resposta na memória
7️⃣  Extrai memórias importantes heuristicamente
8️⃣  Notifica listeners (UI, voz, etc.)
```

**Recursos especiais:**
- **Modo de voz contínuo**: ouve → transcreve → processa → fala (loop)
- **Fila de fala**: processamento assíncrono com fila para evitar sobreposição
- **Fallback de provedores**: se um LLM falha, tenta o próximo automaticamente
- **Memórias automáticas**: detecta preferências do usuário (ex: "meu nome é...")

#### ⚙️ `config.py` — Gerenciamento de Configuração

Carrega e provê acesso centralizado a todas as configurações:

| Fonte | Arquivo | Exemplo |
|---|---|---|
| **JSON** | `shaz/config/settings.json` | Provedor LLM, engine de voz, tema |
| **JSON** | `shaz/config/voice_config.json` | Modelo de voz, fallback chain |
| **.env** | `.env` | Chaves de API (Gemini, OpenAI, etc.) |

```python
# Exemplo de uso
config = Config()
config.llm_provider        # → "gemini"
config.tts_engine          # → "edge"
config.stt_engine          # → "whisper"
config.gemini_api_key      # → "AIza..." (do .env)
config.get("llm.gemini.model")  # → "gemini-2.5-flash"
```

#### 💾 `memory.py` — Sistema de Memória Persistente

**SQLite com cache em memória.** Armazena e recupera todo o contexto da Shaz.

```
🗄️ Tabelas do Banco:
├── users          → Usuários, preferências, last_seen
├── messages       → Histórico completo de conversas
├── memory         → Fatos aprendidos (preferences, facts, knowledge)
├── settings       → Configurações do sistema
└── personality    → Traços de personalidade

🔍 Busca Inteligente:
├── LIKE search por palavras-chave
├── Ordenação por importância + frequência de acesso
├── Expiração automática de memórias temporárias
└── Cache em memória para acesso rápido
```

#### 🎭 `personality.py` — A Alma da Shaz

Contém a **lore completa** (~200 linhas de história) e o sistema de gerenciamento de traços.

```python
# Como a personalidade é usada:
system_prompt = personality.build_system_prompt(
    language="pt-BR",
    extra_context="Data: 08/06/2026",
    memories="Usuário gosta de programação Python",
)
# → Retorna: Lore + Traços + Contexto + Memórias + Instrução de idioma
```

---

### 🎤 voice/ — Sistema de Voz

#### 🎙️ `stt.py` — Speech-to-Text (Escuta)

| Engine | Status | Descrição |
|---|---|---|
| **Faster-Whisper** | ✅ Padrão | Rápido, preciso, modelos base/large |
| **Google Speech** | ✅ Fallback | Gratuito, reconhecimento online |
| **Vosk** | ✅ Alternativa | Offline, leve |

```python
# Como funciona:
audio = recorder.record_speech(timeout=10.0)
text = stt.transcribe_bytes(audio)  # → "Olá Shaz, como você está?"
```

#### 🔊 `tts.py` — Text-to-Speech (Fala)

| Engine | Voz Padrão | Qualidade | Latência |
|---|---|---|---|
| **Edge TTS** | FranciscaNeural | ⭐⭐⭐⭐⭐ | Baixa |
| **gTTS** | Google PT-BR | ⭐⭐⭐⭐ | Média |
| **pyttsx3** | SAPI5 | ⭐⭐⭐ | Instantânea |
| **ElevenLabs** | Personalizada | ⭐⭐⭐⭐⭐ | Média |
| **XTTS** | Clonada | ⭐⭐⭐⭐⭐ | Alta |
| **Piper** | Local | ⭐⭐⭐⭐ | Baixa |

**Sistema de fallback automático** — se um engine falha, tenta o próximo da cadeia.

#### 🎵 `audio.py` — Gerenciamento de Áudio

- **Recorder**: Grava áudio do microfone com detecção de silêncio
- **Player**: Reproduz áudio (bytes, arquivos, streaming)
- **Processador**: Normalização, redução de ruído, conversão de formato

---

### 🔌 services/ — Serviços de Integração

#### 🌐 `api_manager.py` — Gerenciamento de APIs LLM

**Classe principal:** `APIManager` — Gerencia chamadas a múltiplos provedores de IA.

```
📋 Provedores Suportados:
├── OpenAI           → gpt-4o-mini (requer chave)
├── OpenRouter       → Acesso a múltiplos modelos
├── Groq             → LPU Inference (rápido!)
├── Gemini           → gemini-2.5-flash (Google)
└── Ollama           → Local (gratuito, privado)

🔄 Sistema de Fallback:
1. Tenta provedor primário
2. Se falha → tenta próximo disponível
3. Se todos falham → retorna mensagem de erro amigável

⚡ Recursos:
├── Rate Limiting (token bucket)
├── Streaming (chunks em tempo real)
├── Métricas (latência, tokens, modelo)
└── Logging detalhado
```

---

### 🎨 ui/ — Interfaces de Usuário

| Arquivo | Descrição | Tecnologia |
|---|---|---|
| `terminal.py` | Interface de terminal interativa | Rich (Typer) |
| `chat.py` | Widget de chat com bolhas, suporte a markdown | PySide6 (Qt) |
| `dashboard.py` | Dashboard completo: status, logs, CPU, RAM | PySide6 (Qt) |

**Dashboard Desktop inclui:**
- 🔘 Botão liga/desliga
- 🎤 Ativação de voz
- 📊 Monitor de CPU/RAM/MongoDB
- 📝 Logs em tempo real
- 💬 Chat com bolhas de mensagens
- 🔄 Botão de reiniciar conversa

---

### 🛠️ utils/ — Utilitários

| Arquivo | Descrição |
|---|---|
| `helpers.py` | Funções auxiliares: `is_internet_available()`, `get_system_info()`, `format_timestamp()` |
| `logger.py` | Sistema de logging com categorias (system, api, voice, stt, tts, memory, ui), cores e rotação |
| `installer.py` | Instalador automático de dependências para Windows |

---

### 🏛️ providers/ — Provedores de IA

| Diretório | Descrição |
|---|---|
| `llm/` | Implementações concretas de provedores LLM (Gemini, etc.) |
| `voice/` | Adaptadores para diferentes engines de voz |
| `image/` | Geração de imagens (SD local, Replicate, Stability) |

---

## 🚀 Como Usar

### 📦 Instalação Automática (Windows — Recomendado)

```bash
# Clone o repositório
git clone https://github.com/LucasY4N/Shaz.git
cd shaz_ai

# Configure suas chaves de API
cp .env.example .env
# ✏️ Edite .env com suas chaves

# Execute o instalador (faz tudo!)
install_windows.bat
```

### 🐍 Instalação Manual

```bash
# Crie um ambiente virtual
python -m venv venv
.\venv\Scripts\activate

# Instale o Shaz AI com todas as dependências
pip install -e ".[dev]"
```

### 🔄 Suba o MongoDB (para persistência avançada)

```bash
docker run -d -p 27017:27017 --name shaz-mongo mongo:7
```

### 🎮 Modos de Uso

<details>
<summary><b>💬 Modo Chat (CLI)</b></summary>

```bash
python main.py --cli
```
```
╔══════════════════════════════════════╗
║   Shaz AI - Terminal Interativo      ║
║                                      ║
║   Digite sua mensagem ou comandos:   ║
║   • sair   - Encerra                 ║
║   • voz    - Ativa modo de voz       ║
║   • parar  - Para modo de voz        ║
║   • limpar - Limpa histórico         ║
║   • ajuda  - Mostra comandos         ║
╚══════════════════════════════════════╝

Você: Olá Shaz, quem é você?
```
</details>

<details>
<summary><b>🖥️ Modo Desktop (GUI)</b></summary>

```bash
python main.py
```
Abre uma interface gráfica completa com:
- ✅ Dashboard com status em tempo real
- 💬 Chat com bolhas de mensagem
- 🎤 Botão para ativar modo de voz
- 📊 Monitor de CPU/RAM
- 📝 Logs do sistema
</details>

<details>
<summary><b>🔧 Comandos Rápidos</b></summary>

```bash
# Diagnóstico de erro
python main.py diagnose "TypeError: 'NoneType' is not subscriptable"

# Aprender com vídeo do YouTube
python main.py learn https://www.youtube.com/watch?v=SEU_VIDEO

# Dashboard via terminal
python main.py dashboard

# Servidor web
python run_server.py
# → Acesse http://localhost:3000
```
</details>

---

## 🔑 Variáveis de Ambiente

### Configuração Mínima (.env)

```env
# Pelo menos UMA chave de LLM é obrigatória:
GEMINI_API_KEY=AIzaSySeu_Key_Aqui
# OU
GROQ_API_KEY=gsk_Seu_Key_Aqui
# OU
OPENAI_API_KEY=sk-Seu_Key_Aqui
```

### Todas as Variáveis

| Variável | Obrigatório | Padrão | Descrição |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅* | — | Chave da API Google Gemini |
| `GROQ_API_KEY` | ✅* | — | Chave da API Groq |
| `OPENAI_API_KEY` | ✅* | — | Chave da API OpenAI |
| `OPENROUTER_API_KEY` | — | — | Chave OpenRouter |
| `OLLAMA_BASE_URL` | — | `http://localhost:11434` | URL do Ollama local |
| `MONGODB_URI` | — | `mongodb://localhost:27017` | URI do MongoDB |
| `MONGODB_DB` | — | `shaz_ai` | Nome do banco |
| `LOG_LEVEL` | — | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENVIRONMENT` | — | `development` | `development` ou `production` |

> *Pelo menos uma chave de LLM é obrigatória.

---

## 📊 Stack Tecnológica

| Categoria | Tecnologia | Para que serve |
|---|---|---|
| **Linguagem** | Python 3.10+ | Base do projeto |
| **LLM Principal** | Google Gemini (`google-genai`) | IA conversacional |
| **LLM Alternativo** | Groq | Inferência rápida |
| **LLM Clássico** | OpenAI (GPT-4o-mini) | Compatibilidade |
| **LLM Local** | Ollama | Privacidade, offline |
| **Banco Local** | SQLite (com WAL) | Memória persistente |
| **Banco Avançado** | MongoDB (`motor` async) | Persistência extra |
| **CLI** | Typer + Rich | Interface de terminal |
| **Desktop** | PySide6 (Qt) | Interface gráfica |
| **STT** | Faster-Whisper, Google SR, Vosk | Reconhecimento de fala |
| **TTS** | Edge TTS, gTTS, pyttsx3, ElevenLabs, XTTS, Piper | Síntese de voz |
| **Áudio** | PyAudio, soundfile, numpy | Captura e reprodução |
| **Imagens** | Stable Diffusion, Replicate, Stability | Geração de imagens |
| **Vídeos** | yt-dlp, YouTube Transcript | Aprendizado via YouTube |
| **Web** | FastAPI, uvicorn | Servidor HTTP |
| **Electron** | Electron, electron-builder | Empacotamento desktop |
| **Qualidade** | Ruff, Black, mypy, pytest | Lint, formatação, tipos, testes |
| **Segurança** | python-dotenv, pydantic-settings | Gestão de secrets |

---

## 🛠️ Ferramentas de Desenvolvimento

```bash
# Linting e formatação
ruff check .          # Verifica código
black .               # Formata automaticamente

# Type checking
mypy .                # Verifica tipos estáticos

# Testes
pytest -v             # Roda todos os testes
pytest tests/ -v      # Testes específicos

# Pré-commit (instalar uma vez)
pre-commit install    # Hooks automáticos
```

---

## 🤝 Contribuição

Contribuições são bem-vindas! Siga estes passos:

1. 🍴 Fork o projeto
2. 🌿 Crie sua branch (`git checkout -b feature/NovaFuncionalidade`)
3. 💻 Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. 📤 Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. 🔃 Abra um Pull Request

### Diretrizes

- ✅ Siga a arquitetura hexagonal (ports & adapters)
- ✅ Escreva testes para novas funcionalidades
- ✅ Use tipagem estática (type hints)
- ✅ Documente funções e classes
- ✅ Siga o estilo Black + Ruff

---

## 📄 Licença

Distribuído sob licença **MIT**. Veja [LICENSE](LICENSE) para mais informações.

---

## 👨‍💻 Desenvolvedor

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/LucasY4N">
        <img src="https://github.com/LucasY4N.png" width="100px;" alt="LucasY4N"/><br>
        <b>LucasY4N</b>
      </a>
    </td>
  </tr>
</table>

---

<div align="center">

**Shaz AI** — Feito com ☕, 🎧 e muito código

*"A curiosidade é o motor do conhecimento." — Shaz de Pyxis-7*

⭐ **Se este projeto te ajudou, dê uma estrela no GitHub!** ⭐

</div>