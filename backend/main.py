"""
backend/main.py
Ponto de entrada do servidor FastAPI refatorado.
Responsabilidade única: montar a aplicação, registrar rotas, gerenciar lifecycle.

Sem lógica de negócio aqui — tudo delega para serviços e agentes.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Garante que o diretório raiz está no path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config.settings import get_settings
from logs.logger import setup_logger, get_module_logger

settings = get_settings()
setup_logger("shaz", level=settings.log_level, log_file="logs/shaz.log")
log = get_module_logger("backend.main")

# ─── Estado compartilhado ─────────────────────────────────────────────────
_state: dict[str, Any] = {
    "brain": None,
    "weather_service": None,
    "tavily_service": None,
    "github_service": None,
    "wikipedia_service": None,
    "coding_agent": None,
    "stats": {"messages": 0, "tokens": 0},
    # Discord bot state
    "discord_bot": None,
    "discord_bot_thread": None,
    "discord_bot_running": False,
    "discord_bot_error": None,
}
_ws_clients: list[WebSocket] = []

# ─── App ──────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Shaz AI API",
    version=settings.app_version,
    description="API do Shaz AI — assistente inteligente com personalidade.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Logging middleware ────────────────────────────────────────────────────
from backend.middlewares.logging_middleware import logging_middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)


# ─── Lifecycle ────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup() -> None:
    log.info("Starting Shaz AI server...")
    _initialize_brain()
    _initialize_external_services()
    _initialize_agents()
    log.info(f"Server ready on http://{settings.server_host}:{settings.server_port}")


@app.on_event("shutdown")
async def shutdown() -> None:
    brain = _state.get("brain")
    if brain and hasattr(brain, "shutdown"):
        brain.shutdown()

    # Fecha clientes HTTP
    for svc_key in ("weather_service", "tavily_service", "github_service", "wikipedia_service"):
        svc = _state.get(svc_key)
        if svc and hasattr(svc, "close"):
            await svc.close()

    log.info("Shaz AI server shutdown complete.")


def _initialize_brain() -> None:
    """Inicializa o ShazBrain (importação lazy para não quebrar se módulos ausentes)."""
    try:
        # Importa a partir da estrutura original (mantém compatibilidade)
        sys.path.insert(0, str(_root.parent))
        from shaz.core.brain import ShazBrain
        from shaz.core.config import Config
        from shaz.core.memory import Memory
        from shaz.core.personality import Personality

        config = Config()
        db_path = str(config.data_path / "memory.db")
        memory = Memory(db_path)
        personality = Personality(memory)

        brain = ShazBrain(config=config, memory=memory, personality=personality)
        brain.set_on_status_change(
            lambda s: asyncio.ensure_future(_broadcast({"type": "status", "status": s}))
        )
        _state["brain"] = brain
        log.info("ShazBrain initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize ShazBrain: {e}")


def _initialize_external_services() -> None:
    """Inicializa APIs externas conforme chaves disponíveis."""
    if settings.has_weather:
        from apis.weather.service import WeatherService
        _state["weather_service"] = WeatherService(settings.openweather_api_key)
        log.info("WeatherService initialized")

    if settings.has_tavily:
        from apis.tavily.service import TavilyService
        _state["tavily_service"] = TavilyService(settings.tavily_api_key)
        log.info("TavilyService initialized")

    if settings.has_github:
        from apis.github.service import GitHubService
        _state["github_service"] = GitHubService(settings.github_token)
        log.info("GitHubService initialized")

    # Wikipedia: sem chave necessária
    from apis.wikipedia.service import WikipediaService
    _state["wikipedia_service"] = WikipediaService()
    log.info("WikipediaService initialized")


def _initialize_agents() -> None:
    """Inicializa os agentes com as dependências disponíveis."""
    brain = _state.get("brain")
    if not brain:
        return

    from agents.coding_agent import CodingAgent
    _state["coding_agent"] = CodingAgent(brain._api)

    from agents.research_agent import ResearchAgent
    _state["research_agent"] = ResearchAgent(
        llm_service=brain._api,
        tavily_service=_state.get("tavily_service"),
        wikipedia_service=_state.get("wikipedia_service"),
        github_service=_state.get("github_service"),
    )

    from agents.memory_agent import MemoryAgent
    _state["memory_agent"] = MemoryAgent(brain._memory)

    from agents.system_agent import SystemAgent
    _state["system_agent"] = SystemAgent()

    log.info("All agents initialized")


# ─── Rotas ───────────────────────────────────────────────────────────────
from backend.routes import chat as chat_route
from backend.routes import tools as tools_route
from backend.routes import stats as stats_route
from backend.routes import voice as voice_route
from backend.routes import screen as screen_route
from backend.routes import discord as discord_route

app.include_router(chat_route.register(_state), prefix="/api")
app.include_router(tools_route.register(_state), prefix="/api")
app.include_router(stats_route.register(_state), prefix="/api")
app.include_router(voice_route.register(_state), prefix="/api")
app.include_router(screen_route.register(_state), prefix="/api")
app.include_router(discord_route.register(_state), prefix="/api")


@app.get("/")
async def root() -> dict:
    return {"status": "online", "app": "Shaz AI", "version": settings.app_version}


# ── Serve HTML ────────────────────────────────────────────────────────────
_html_path = _root / "shaz-terminal.html"

@app.get("/app")
async def serve_html():
    if _html_path.exists():
        return FileResponse(str(_html_path))
    return JSONResponse(status_code=404, content={"error": "shaz-terminal.html not found"})


# ─── WebSocket ────────────────────────────────────────────────────────────
async def _broadcast(data: dict) -> None:
    message = json.dumps(data, ensure_ascii=False)
    for ws in list(_ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            _ws_clients.discard(ws) if hasattr(_ws_clients, "discard") else None


_state["broadcast"] = _broadcast


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    _ws_clients.append(ws)
    log.info(f"WS client connected ({len(_ws_clients)} total)")

    try:
        await ws.send_text(json.dumps({
            "type": "connected",
            "message": f"Shaz AI {settings.app_version} — conectado",
        }))

        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type", "chat")

            if msg_type == "chat":
                brain = _state.get("brain")
                text = msg.get("message", "").strip()
                if text and brain:
                    response = await brain.process_message(text)
                    await ws.send_text(json.dumps({"type": "response", "response": response}))

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "exec":
                # Terminal: execução segura limitada a comandos de status
                cmd = msg.get("cmd", "").strip()
                await _handle_terminal_command(ws, cmd)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"WS error: {e}")
    finally:
        try:
            _ws_clients.remove(ws)
        except ValueError:
            pass
        log.info(f"WS client disconnected ({len(_ws_clients)} remaining)")


async def _handle_terminal_command(ws: WebSocket, cmd: str) -> None:
    """Executa comandos seguros no terminal do dashboard."""
    import subprocess, shlex

    # Allowlist de comandos permitidos
    SAFE_PREFIXES = ("python", "pip", "ls", "dir", "cat", "echo", "pwd")
    parts = shlex.split(cmd) if cmd else []

    if not parts or not any(cmd.startswith(p) for p in SAFE_PREFIXES):
        await ws.send_text(json.dumps({
            "type": "terminal_err",
            "text": f"Comando não permitido: {cmd}",
        }))
        await ws.send_text(json.dumps({"type": "terminal_done"}))
        return

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(_root.parent),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if stdout:
            for line in stdout.decode("utf-8", errors="replace").splitlines():
                await ws.send_text(json.dumps({"type": "terminal_out", "text": line}))
        if stderr:
            for line in stderr.decode("utf-8", errors="replace").splitlines():
                await ws.send_text(json.dumps({"type": "terminal_err", "text": line}))
    except asyncio.TimeoutError:
        await ws.send_text(json.dumps({"type": "terminal_err", "text": "Timeout (30s)"}))
    except Exception as e:
        await ws.send_text(json.dumps({"type": "terminal_err", "text": str(e)}))
    finally:
        await ws.send_text(json.dumps({"type": "terminal_done"}))
