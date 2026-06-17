# INSTALLATION.md

## Requisitos

- Python 3.11+
- pip
- FFmpeg (para conversão de áudio)

---

## Instalação Rápida (Windows)

```bash
git clone https://github.com/LucasY4N/Shaz.git
cd shaz_ai
cp .env.example .env
# Edite .env com suas chaves de API
install_windows.bat
```

---

## Instalação Manual

```bash
# 1. Ambiente virtual
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/macOS

# 2. Dependências
pip install -r requirements.txt

# 3. Dependências opcionais de voz
pip install faster-whisper edge-tts sounddevice soundfile pygame

# 4. Configuração
cp .env.example .env
# Edite .env com suas chaves
```

---

## Configuração mínima do .env

```env
# Pelo menos UMA chave LLM é obrigatória:
GEMINI_API_KEY="sua-chave-aqui"
# OU
GROQ_API_KEY="sua-chave-aqui"
```

## Configuração completa (todas as funcionalidades)

```env
# LLM
GEMINI_API_KEY=""
GROQ_API_KEY=""

# APIs externas
GITHUB_TOKEN=""            # Análise de repos GitHub
OPENWEATHER_API_KEY=""     # Clima
TAVILY_API_KEY=""          # Pesquisa web

# Servidor
SERVER_PORT=8765
LOG_LEVEL=INFO
```

---

## Como Iniciar

### Servidor web (recomendado)
```bash
python run_server_new.py
# Abre http://localhost:8765/app automaticamente
```

### Interface desktop
```bash
python main.py
```

### Modo terminal
```bash
python main.py --cli
```

---

## Onde obter as chaves de API

| API | URL | Plano gratuito |
|-----|-----|----------------|
| Gemini | https://aistudio.google.com/app/apikey | Sim |
| Groq | https://console.groq.com/keys | Sim |
| OpenAI | https://platform.openai.com/api-keys | Pago |
| GitHub | https://github.com/settings/tokens | Sim |
| OpenWeatherMap | https://openweathermap.org/api | Sim (1000 req/dia) |
| Tavily | https://app.tavily.com | Sim (1000 req/mês) |

---

## Solução de Problemas

**Erro: `ModuleNotFoundError: No module named 'faster_whisper'`**
```bash
pip install faster-whisper
```

**Erro: `pyaudio` no Windows**
```bash
pip install pipwin
pipwin install pyaudio
```

**Erro: `edge-tts` não fala**
```bash
pip install --upgrade edge-tts
```

**TTS muito lento (XTTS)**
```
Use engine "edge" (padrão) — XTTS é para clonagem de voz avançada.
```
