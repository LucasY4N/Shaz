"""
shaz/server.py  ← substitua o arquivo existente por este

FIXES APLICADOS:
  1. Favicon adicionado (/favicon.ico)
  2. Voz automática DESABILITADA — só fala quando /api/voice/test ou /api/voice/start
  3. /api/chat NÃO mais aciona TTS automaticamente
  4. Rota /api/voice/cloned/list para listar vozes clonadas
  5. Rota /api/voice/cloned/select para selecionar voz clonada ativa
  6. Rota /api/voice/cloned/create para clonar uma nova voz
  7. Estado da voz clonada ativa persiste entre chamadas
  8. WebSocket: mensagem speaking_started / speaking_stopped enviada corretamente
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel

from shaz.core.brain import ShazBrain
from shaz.core.config import Config
from shaz.core.memory import Memory
from shaz.core.personality import Personality
from shaz.utils.logger import logger

# ─── APP ─────────────────────────────────────────────────────────────────
app = FastAPI(title="Shaz AI API", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ──────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    tokens: int = 0

class ProviderRequest(BaseModel):
    provider: str

class VoiceRequest(BaseModel):
    voice: str

class EngineRequest(BaseModel):
    engine: str

class PromptRequest(BaseModel):
    prompt: str

class ClonedVoiceSelectRequest(BaseModel):
    profile_id: str

class ClonedVoiceCreateRequest(BaseModel):
    audio_base64: str     # Áudio codificado em base64
    name: str
    language: str = "pt"
    description: str = ""

# ─── Estado Global ────────────────────────────────────────────────────────
_brain: Optional[ShazBrain] = None
_brain_lock = threading.Lock()
_ws_clients: List[WebSocket] = []
_active_cloned_voice_id: Optional[str] = None   # ID da voz clonada ativa

# Discord bot state
_discord_bot_running: bool = False
_discord_bot_error: Optional[str] = None
_discord_bot_thread: Optional[threading.Thread] = None

_stats: Dict[str, Any] = {
    "messages": 0,
    "tokens": 0,
    "memories": 0,
}


def get_brain() -> ShazBrain:
    global _brain
    if _brain is None:
        with _brain_lock:
            if _brain is None:
                logger.info("[Server] Inicializando ShazBrain...")
                config = Config()
                db_path = str(config.data_path / "memory.db")
                memory = Memory(db_path)
                personality = Personality(memory)
                brain = ShazBrain(
                    config=config,
                    memory=memory,
                    personality=personality,
                )
                brain.set_on_status_change(lambda s: _broadcast_sync({"type": "status", "status": s}))
                brain.set_on_response(lambda r: _broadcast_sync({"type": "response", "response": r}))
                _brain = brain
                logger.info("[Server] ShazBrain pronto!")
    return _brain


# ─── WebSocket Broadcast ──────────────────────────────────────────────────
async def _broadcast(data: dict) -> None:
    message = json.dumps(data, ensure_ascii=False)
    for ws in list(_ws_clients):
        try:
            await ws.send_text(message)
        except Exception:
            try:
                _ws_clients.remove(ws)
            except ValueError:
                pass


def _broadcast_sync(data: dict) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(data))
        else:
            loop.run_until_complete(_broadcast(data))
    except RuntimeError:
        asyncio.run(_broadcast(data))


# ─── Eventos ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("[Server] Shaz AI HTTP v3.1 iniciado — TTS automático DESABILITADO")


@app.on_event("shutdown")
async def shutdown():
    global _brain
    if _brain:
        logger.info("[Server] Encerrando ShazBrain...")


# ─── Favicon ─────────────────────────────────────────────────────────────
# Favicon em base64 (ícone rosa S de 32x32 embutido para não depender de arquivo externo)
_FAVICON_B64 = (
    "AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    # PNG mínimo 1x1 transparente serve como fallback funcional
)

_FAVICON_PATH = _root / "assets" / "favicon.ico"
_FAVICON_PNG_PATH = _root / "assets" / "favicon.png"


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Serve o favicon."""
    if _FAVICON_PATH.exists():
        return FileResponse(str(_FAVICON_PATH))
    if _FAVICON_PNG_PATH.exists():
        return FileResponse(str(_FAVICON_PNG_PATH))
    # Fallback: PNG 1x1 transparente para não dar 404
    png_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    return Response(content=png_1x1, media_type="image/png")


# ─── Chat — SEM TTS automático ────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "online", "app": "Shaz AI", "version": "3.1.0"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> dict:
    """
    Processa mensagem e retorna resposta em texto.
    ⚠ NÃO aciona TTS automaticamente — voz só quando /api/voice/speak é chamado.
    """
    if not request.message.strip():
        return {"response": "...", "tokens": 0}

    brain = get_brain()
    response = await brain.process_message(request.message)

    _stats["messages"] += 1
    _stats["tokens"] += len(request.message) + len(response)

    _broadcast_sync({
        "type": "chat",
        "user": request.message,
        "assistant": response,
        "tokens": _stats["tokens"],
    })

    return {"response": response, "tokens": _stats["tokens"]}


@app.post("/api/voice/speak")
async def voice_speak(request: ChatRequest) -> dict:
    """
    Sintetiza um texto específico com a voz ativa (clonada ou padrão).
    Chame EXPLICITAMENTE quando quiser ouvir a Shaz falar.
    """
    brain = get_brain()
    text = request.message.strip()
    if not text:
        return {"status": "error", "message": "Texto vazio"}

    try:
        global _active_cloned_voice_id

        if _active_cloned_voice_id:
            # Usa voz clonada
            from shaz.voice_cloner import VoiceCloner
            cloner = VoiceCloner()
            audio = await cloner.synthesize(text, _active_cloned_voice_id)
        else:
            # Usa Edge TTS padrão
            audio = await brain._tts.synthesize(text)

        if audio:
            _broadcast_sync({"type": "speaking_started", "text": text[:60]})
            await asyncio.to_thread(brain._audio.player.play_bytes, audio)
            _broadcast_sync({"type": "speaking_stopped"})
            return {"status": "ok", "bytes": len(audio)}
        else:
            return {"status": "error", "message": "Síntese falhou"}

    except Exception as e:
        logger.error(f"[Server] voice_speak error: {e}")
        return {"status": "error", "message": str(e)}


# ─── Rotas de Voz Clonada ─────────────────────────────────────────────────
@app.get("/api/voice/cloned/list")
async def list_cloned_voices() -> dict:
    """Lista todas as vozes clonadas salvas."""
    try:
        from shaz.voice_cloner import VoiceCloner
        cloner = VoiceCloner()
        profiles = cloner.list_profiles()
        return {
            "profiles": [
                {
                    "id": p.id,
                    "name": p.name,
                    "language": p.language,
                    "duration": p.duration_seconds,
                    "created_at": p.created_at,
                    "description": p.description,
                    "active": p.id == _active_cloned_voice_id,
                }
                for p in profiles
            ],
            "active_id": _active_cloned_voice_id,
        }
    except Exception as e:
        return {"profiles": [], "active_id": None, "error": str(e)}


@app.post("/api/voice/cloned/select")
async def select_cloned_voice(req: ClonedVoiceSelectRequest) -> dict:
    """
    Define qual voz clonada usar. Passe profile_id="" para voltar ao padrão (Edge TTS).
    """
    global _active_cloned_voice_id

    if not req.profile_id:
        _active_cloned_voice_id = None
        _broadcast_sync({"type": "voice_changed", "voice": "edge_default", "cloned": False})
        return {"status": "ok", "message": "Voltando para voz padrão (Edge TTS)"}

    try:
        from shaz.voice_cloner import VoiceCloner
        cloner = VoiceCloner()
        profile = cloner.get_profile(req.profile_id)
        if not profile:
            return {"status": "error", "message": f"Perfil '{req.profile_id}' não encontrado"}

        _active_cloned_voice_id = req.profile_id
        _broadcast_sync({
            "type": "voice_changed",
            "voice": profile.name,
            "cloned": True,
            "profile_id": req.profile_id,
        })
        logger.info(f"[Server] Voz clonada ativa: {profile.name} ({req.profile_id})")
        return {"status": "ok", "message": f"Voz '{profile.name}' ativada", "profile": {
            "id": profile.id,
            "name": profile.name,
            "language": profile.language,
        }}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/cloned/create")
async def create_cloned_voice(req: ClonedVoiceCreateRequest) -> dict:
    """
    Cria uma nova voz clonada a partir de áudio em base64.
    O frontend envia o arquivo de referência codificado em base64.
    """
    try:
        from shaz.voice_cloner import VoiceCloner
        import tempfile, base64

        # Decodifica o áudio
        audio_bytes = base64.b64decode(req.audio_base64)

        # Salva temporariamente
        suffix = ".wav"
        if audio_bytes[:3] == b"ID3" or (len(audio_bytes) > 1 and audio_bytes[0] == 0xFF):
            suffix = ".mp3"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name

        cloner = VoiceCloner()
        profile = await cloner.create_profile(
            audio_path=temp_path,
            name=req.name,
            language=req.language,
            description=req.description,
        )

        # Remove temporário
        try:
            os.unlink(temp_path)
        except Exception:
            pass

        logger.info(f"[Server] Voz clonada criada: {profile.name} ({profile.id})")
        _broadcast_sync({
            "type": "voice_cloned",
            "profile_id": profile.id,
            "name": profile.name,
        })

        return {
            "status": "ok",
            "profile": {
                "id": profile.id,
                "name": profile.name,
                "language": profile.language,
                "duration": profile.duration_seconds,
            }
        }

    except Exception as e:
        logger.error(f"[Server] create_cloned_voice error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/cloned/delete")
async def delete_cloned_voice(req: ClonedVoiceSelectRequest) -> dict:
    """Remove uma voz clonada."""
    global _active_cloned_voice_id
    try:
        from shaz.voice_cloner import VoiceCloner
        cloner = VoiceCloner()
        if cloner.delete_profile(req.profile_id):
            if _active_cloned_voice_id == req.profile_id:
                _active_cloned_voice_id = None
            return {"status": "ok"}
        return {"status": "error", "message": "Perfil não encontrado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/cloned/test")
async def test_cloned_voice(req: ClonedVoiceSelectRequest) -> dict:
    """Testa uma voz clonada com uma frase de exemplo."""
    try:
        from shaz.voice_cloner import VoiceCloner
        brain = get_brain()
        cloner = VoiceCloner()
        audio = await cloner.synthesize(
            "Olá! Esta é minha voz clonada pela Shaz AI.",
            req.profile_id,
        )
        if audio:
            await asyncio.to_thread(brain._audio.player.play_bytes, audio)
            return {"status": "ok", "bytes": len(audio)}
        return {"status": "error", "message": "Síntese falhou"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── Rotas do Discord Bot ─────────────────────────────────────────────────
@app.get("/api/discord/status")
async def discord_status():
    """Retorna o status atual do Discord bot."""
    global _discord_bot_running, _discord_bot_error
    return {
        "running": _discord_bot_running,
        "error": _discord_bot_error,
    }


@app.post("/api/discord/start")
async def discord_start():
    """Inicia o Discord bot em uma thread separada."""
    global _discord_bot_running, _discord_bot_error, _discord_bot_thread

    if _discord_bot_running:
        return {"status": "ok", "message": "Discord bot já está rodando"}

    # Limpa erro anterior
    _discord_bot_error = None

    try:
        from discord_bot.bot.bot import ShazBot
        from discord_bot.config.settings import get_discord_settings
    except ImportError as e:
        _discord_bot_error = f"Erro ao importar módulos do Discord: {e}"
        return {"status": "error", "message": _discord_bot_error}

    settings = get_discord_settings()
    if not settings.has_token:
        _discord_bot_error = "DISCORD_TOKEN não configurado no .env"
        return {
            "status": "error",
            "message": "DISCORD_TOKEN não configurado no .env",
        }

    def run_bot():
        """Roda o bot nesta thread (bloqueante)."""
        import asyncio as _asyncio

        bot = ShazBot()

        async def _start():
            try:
                await bot.start(settings.discord_token)
            except Exception as e:
                global _discord_bot_error, _discord_bot_running
                _discord_bot_error = str(e)
                _discord_bot_running = False
            finally:
                if not bot.is_closed():
                    await bot.close()
                _discord_bot_running = False

        try:
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            loop.run_until_complete(_start())
        except Exception as e:
            global _discord_bot_error, _discord_bot_running
            _discord_bot_error = str(e)
            _discord_bot_running = False

    t = threading.Thread(target=run_bot, daemon=True, name="discord-bot")
    t.start()

    _discord_bot_running = True
    _discord_bot_thread = t

    # Broadcast para a interface web
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast({
                "type": "discord_status",
                "running": True,
                "error": None,
            }))
    except RuntimeError:
        pass

    return {"status": "ok", "message": "Discord bot iniciado com sucesso"}


@app.post("/api/discord/stop")
async def discord_stop():
    """Para o Discord bot."""
    global _discord_bot_running

    if not _discord_bot_running:
        return {"status": "ok", "message": "Discord bot não está rodando"}

    _discord_bot_running = False

    # Broadcast para a interface web
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast({
                "type": "discord_status",
                "running": False,
                "error": None,
            }))
    except RuntimeError:
        pass

    return {
        "status": "ok",
        "message": "Sinal de parada enviado ao Discord bot (thread encerrando)",
    }


# ─── Demais rotas existentes ─────────────────────────────────────────────
@app.get("/api/stats")
async def get_stats() -> dict:
    brain = get_brain()
    try:
        brain_stats = brain.get_stats() if hasattr(brain, "get_stats") else {}
    except Exception:
        brain_stats = {}
    return {"messages": _stats["messages"], "tokens": _stats["tokens"], "memories": _stats["memories"], **brain_stats}


@app.get("/api/memories")
async def get_memories() -> list:
    brain = get_brain()
    try:
        memories = brain.get_memories() if hasattr(brain, "get_memories") else []
    except Exception:
        memories = []
    result = []
    for m in memories[:50]:
        result.append({
            "content": m.get("content", str(m)) if isinstance(m, dict) else str(m),
            "type": m.get("memory_type", m.get("type", "general")) if isinstance(m, dict) else "general",
            "time": m.get("created_at", m.get("time", "")) if isinstance(m, dict) else "",
        })
    _stats["memories"] = len(result)
    return result


@app.get("/api/personality")
async def get_personality() -> dict:
    brain = get_brain()
    try:
        personality = brain.personality if hasattr(brain, "personality") else None
        if personality and hasattr(personality, "traits"):
            return personality.traits
    except Exception:
        pass
    return {
        "name": "Shaz", "origin_planet": "Pyxis-7",
        "personality_type": "introvert", "intelligence_level": "exceptional",
        "expertise": "technology, programming, AI, quantum computing",
        "communication_style": "natural, friendly, humble, occasionally shy",
        "core_values": "kindness, honesty, curiosity, respect",
        "favorite_topics": "programming, science, mathematics, sci-fi",
    }


@app.post("/api/clear")
async def clear_history() -> dict:
    brain = get_brain()
    try:
        if hasattr(brain, "clear_history"):
            brain.clear_history()
    except Exception:
        pass
    _stats["messages"] = 0
    _broadcast_sync({"type": "cleared"})
    return {"status": "ok"}


@app.get("/api/providers")
async def get_providers() -> dict:
    brain = get_brain()
    try:
        api = brain.api if hasattr(brain, "api") else None
        available = api.available_providers if (api and hasattr(api, "available_providers")) else []
        current = api.current_provider if (api and hasattr(api, "current_provider")) else ""
        return {"available": available, "current": current}
    except Exception as e:
        return {"available": [], "current": "", "error": str(e)}


@app.post("/api/provider")
async def set_provider(req: ProviderRequest) -> dict:
    brain = get_brain()
    try:
        if hasattr(brain, "set_provider"):
            ok = brain.set_provider(req.provider)
            return {"status": "ok" if ok else "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "error"}


@app.post("/api/voice/set")
async def set_voice(req: VoiceRequest) -> dict:
    brain = get_brain()
    try:
        tts = brain._tts if hasattr(brain, "_tts") else None
        if tts and hasattr(tts, "set_voice"):
            tts.set_voice(req.voice)
    except Exception:
        pass
    _broadcast_sync({"type": "voice_set", "voice": req.voice})
    return {"status": "ok", "voice": req.voice}


@app.post("/api/engine/set")
async def set_engine(req: EngineRequest) -> dict:
    brain = get_brain()
    try:
        tts = brain._tts if hasattr(brain, "_tts") else None
        if tts and hasattr(tts, "set_engine"):
            tts.set_engine(req.engine)
    except Exception:
        pass
    _broadcast_sync({"type": "engine_set", "engine": req.engine})
    return {"status": "ok", "engine": req.engine}


@app.post("/api/voice/test")
async def test_voice() -> dict:
    """Testa a voz PADRÃO (Edge TTS). Para testar voz clonada use /api/voice/cloned/test."""
    brain = get_brain()
    try:
        audio = await brain._tts.synthesize("Olá! Eu sou a Shaz. Teste de voz completo.")
        if audio:
            await asyncio.to_thread(brain._audio.player.play_bytes, audio)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/stop_speaking")
async def stop_speaking() -> dict:
    brain = get_brain()
    try:
        if hasattr(brain, "_audio") and brain._audio:
            brain._audio.player.stop()
        if hasattr(brain, "_speak_queue") and brain._speak_queue:
            while not brain._speak_queue.empty():
                try:
                    brain._speak_queue.get_nowait()
                except Exception:
                    pass
    except Exception:
        pass
    _broadcast_sync({"type": "speaking_stopped"})
    return {"status": "ok"}


@app.post("/api/voice/start")
async def voice_start() -> dict:
    brain = get_brain()
    try:
        if brain.is_voice_active:
            return {"status": "ok", "message": "Voz já ativa"}
        _broadcast_sync({"type": "status", "status": "listening"})
        asyncio.ensure_future(brain.process_voice())
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/stop")
async def voice_stop() -> dict:
    brain = get_brain()
    try:
        brain.stop_voice_mode()
        _broadcast_sync({"type": "status", "status": "online"})
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/voice/status")
async def voice_status() -> dict:
    brain = get_brain()
    return {
        "voice_active": brain.is_voice_active if hasattr(brain, "is_voice_active") else False,
        "cloned_voice_id": _active_cloned_voice_id,
    }


@app.post("/api/personality/prompt")
async def set_system_prompt(req: PromptRequest) -> dict:
    try:
        brain = get_brain()
        personality = brain.personality if hasattr(brain, "personality") else None
        if personality and hasattr(personality, "set_system_prompt"):
            personality.set_system_prompt(req.prompt)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/status")
async def system_status() -> dict:
    brain = get_brain()
    try:
        stats = brain.get_stats() if hasattr(brain, "get_stats") else {}
        voice_active = brain.is_voice_active if hasattr(brain, "is_voice_active") else False
        config = brain.config if hasattr(brain, "config") else None
    except Exception:
        stats = {}
        voice_active = False
        config = None
    return {
        "online": True,
        "voice_active": voice_active,
        "messages_session": _stats["messages"],
        "tokens_session": _stats["tokens"],
        "providers": stats.get("providers", []),
        "current_provider": stats.get("current_provider", "unknown"),
        "cloned_voice_id": _active_cloned_voice_id,
        "version": "3.1.0",
    }


# ─── WebSocket ────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    logger.info(f"[WS] Cliente conectado ({len(_ws_clients)} total)")
    try:
        await ws.send_text(json.dumps({
            "type": "connected",
            "message": "Conectado ao Shaz AI NEXUS v3.1",
            "clients": len(_ws_clients),
        }))
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            msg_type = msg.get("type", "chat")
            if msg_type == "chat":
                text = msg.get("message", "").strip()
                if not text:
                    continue
                brain = get_brain()
                response = await brain.process_message(text)
                await ws.send_text(json.dumps({"type": "response", "response": response, "user": text}))
            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            elif msg_type == "clear":
                brain = get_brain()
                if hasattr(brain, "clear_history"):
                    brain.clear_history()
                await ws.send_text(json.dumps({"type": "cleared"}))
            elif msg_type == "exec":
                cmd = msg.get("cmd", "").strip()
                if cmd:
                    import subprocess
                    try:
                        proc = await asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stdout, stderr = await proc.communicate()
                        if stdout:
                            for line in stdout.decode(errors="replace").split("\n"):
                                if line:
                                    await ws.send_text(json.dumps({"type": "terminal_out", "text": line}))
                        if stderr:
                            for line in stderr.decode(errors="replace").split("\n"):
                                if line:
                                    await ws.send_text(json.dumps({"type": "terminal_err", "text": line}))
                        await ws.send_text(json.dumps({"type": "terminal_done"}))
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "terminal_err", "text": str(e)}))
                        await ws.send_text(json.dumps({"type": "terminal_done"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
    finally:
        try:
            _ws_clients.remove(ws)
        except ValueError:
            pass


# ─── HTML App ─────────────────────────────────────────────────────────────
_html_path = _root / "shaz-terminal.html"

@app.get("/app")
async def serve_html():
    if _html_path.exists():
        return FileResponse(str(_html_path))
    return JSONResponse(status_code=404, content={"error": "shaz-terminal.html not found"})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SHAZ_PORT", 8765))
    host = os.environ.get("SHAZ_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="info")
