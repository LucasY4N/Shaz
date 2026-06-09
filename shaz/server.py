"""
shaz/server.py
FastAPI + WebSocket server que expõe o ShazAI como API REST.
Permite que o shaz-terminal.html se comunique com o backend Python real.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Garante que o diretório raiz está no path
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from shaz.core.brain import ShazBrain
from shaz.core.config import Config
from shaz.core.memory import Memory
from shaz.core.personality import Personality
from shaz.services.api_manager import APIManager
from shaz.utils.logger import logger

# ─── APP ──────────────────────────────────────────────────────────────────
app = FastAPI(title="Shaz AI API", version="3.0.0")

# CORS — permite o HTML de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────
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

class EmptyRequest(BaseModel):
    pass


# ─── Brain Singleton ─────────────────────────────────────────────────────
_brain: Optional[ShazBrain] = None
_brain_lock = threading.Lock()
_ws_clients: List[WebSocket] = []
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
                logger.info("[Server] Inicializando ShazBrain para o servidor HTTP...")
                config = Config()
                
                # Inicializa os componentes manualmente
                from pathlib import Path as P
                db_path = str(config.data_path / "memory.db")
                memory = Memory(db_path)
                personality = Personality(memory)
                
                # Cria o brain
                brain = ShazBrain(
                    config=config,
                    memory=memory,
                    personality=personality,
                )
                
                # Callbacks para broadcast
                brain.set_on_status_change(lambda s: _broadcast_sync({"type": "status", "status": s}))
                brain.set_on_response(lambda r: _broadcast_sync({"type": "response", "response": r}))
                
                _brain = brain
                logger.info("[Server] ShazBrain pronto para o servidor HTTP!")
    return _brain


# ─── WebSocket Broadcast ──────────────────────────────────────────────────
async def _broadcast(data: dict) -> None:
    """Envia mensagem para todos os WebSockets conectados."""
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
    """Versão síncrona - cria task em loop existente ou chama diretamente."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_broadcast(data))
        else:
            loop.run_until_complete(_broadcast(data))
    except RuntimeError:
        # Sem loop rodando - cria um novo
        asyncio.run(_broadcast(data))


# ─── Eventos de inicialização ────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    logger.info("[Server] Servidor Shaz AI HTTP iniciado!")

@app.on_event("shutdown")
async def shutdown():
    global _brain
    if _brain:
        _brain.shutdown() if hasattr(_brain, 'shutdown') else None
        logger.info("[Server] ShazBrain desligado.")


# ─── Rotas REST ──────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """Redireciona para o HTML ou mostra status."""
    return {"status": "online", "app": "Shaz AI", "version": "3.0.0"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> dict:
    """Processa uma mensagem e retorna resposta da Shaz."""
    if not request.message.strip():
        return {"response": "...", "tokens": 0}
    
    brain = get_brain()
    response = await brain.process_message(request.message)
    
    _stats["messages"] += 1
    _stats["tokens"] += len(request.message) + len(response)
    
    # Broadcast de status
    _broadcast_sync({
        "type": "chat",
        "user": request.message,
        "assistant": response,
        "tokens": _stats["tokens"],
    })
    
    return {"response": response, "tokens": _stats["tokens"]}


@app.get("/api/stats")
async def get_stats() -> dict:
    """Retorna estatísticas do sistema."""
    brain = get_brain()
    try:
        brain_stats = brain.get_stats() if hasattr(brain, 'get_stats') else {}
    except Exception:
        brain_stats = {}
    
    return {
        "messages": _stats["messages"],
        "tokens": _stats["tokens"],
        "memories": _stats["memories"],
        **brain_stats,
    }


@app.get("/api/memories")
async def get_memories() -> list:
    """Retorna memórias salvas."""
    brain = get_brain()
    try:
        memories = brain.get_memories() if hasattr(brain, 'get_memories') else []
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
    """Retorna traços de personalidade."""
    brain = get_brain()
    try:
        personality = brain.personality if hasattr(brain, 'personality') else None
        if personality and hasattr(personality, 'traits'):
            return personality.traits
        # Fallback: traits padrão
    except Exception:
        pass
    
    return {
        "name": "Shaz",
        "origin_planet": "Pyxis-7",
        "personality_type": "introvert",
        "intelligence_level": "exceptional",
        "expertise": "technology, programming, AI, quantum computing",
        "communication_style": "natural, friendly, humble, occasionally shy",
        "core_values": "kindness, honesty, curiosity, respect",
        "favorite_topics": "programming, science, mathematics, sci-fi",
    }


@app.post("/api/clear")
async def clear_history() -> dict:
    """Limpa histórico de conversa."""
    brain = get_brain()
    try:
        if hasattr(brain, 'clear_history'):
            brain.clear_history()
    except Exception:
        pass
    
    _stats["messages"] = 0
    _broadcast_sync({"type": "cleared"})
    return {"status": "ok", "message": "Histórico limpo"}


@app.post("/api/provider")
async def set_provider(req: ProviderRequest) -> dict:
    """Troca o provedor LLM."""
    brain = get_brain()
    try:
        if hasattr(brain, 'set_provider'):
            ok = brain.set_provider(req.provider)
            return {"status": "ok" if ok else "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "Provider not supported"}


@app.get("/api/providers")
async def get_providers() -> dict:
    """Lista provedores disponíveis."""
    brain = get_brain()
    try:
        api = brain.api if hasattr(brain, 'api') else None
        available = api.available_providers if (api and hasattr(api, 'available_providers')) else []
        current = api.current_provider if (api and hasattr(api, 'current_provider')) else ""
        return {
            "available": available,
            "current": current,
        }
    except Exception as e:
        return {"available": [], "current": "", "error": str(e)}


@app.get("/api/voices")
async def get_voices() -> list:
    """Lista vozes disponíveis para TTS."""
    # Edge TTS vozes PT-BR + algumas internacionais
    return [
        {"id": "pt-BR-FranciscaNeural", "name": "Francisca (Feminina)", "locale": "pt-BR", "gender": "female"},
        {"id": "pt-BR-ThalitaNeural", "name": "Thalita (Feminina)", "locale": "pt-BR", "gender": "female"},
        {"id": "pt-BR-AntonioNeural", "name": "Antonio (Masculino)", "locale": "pt-BR", "gender": "male"},
        {"id": "pt-PT-FernandaNeural", "name": "Fernanda (Portuguesa)", "locale": "pt-PT", "gender": "female"},
        {"id": "en-US-JennyNeural", "name": "Jenny (English)", "locale": "en-US", "gender": "female"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher (English)", "locale": "en-US", "gender": "male"},
    ]


@app.post("/api/voice/set")
async def set_voice(req: VoiceRequest) -> dict:
    """Define a voz do TTS."""
    brain = get_brain()
    try:
        tts = brain._tts if hasattr(brain, '_tts') else None
        if tts and hasattr(tts, 'set_voice'):
            tts.set_voice(req.voice)
    except Exception:
        pass
    _broadcast_sync({"type": "voice_set", "voice": req.voice})
    return {"status": "ok", "voice": req.voice}


@app.post("/api/engine/set")
async def set_engine(req: EngineRequest) -> dict:
    """Define o mecanismo TTS."""
    brain = get_brain()
    try:
        tts = brain._tts if hasattr(brain, '_tts') else None
        if tts and hasattr(tts, 'set_engine'):
            tts.set_engine(req.engine)
    except Exception:
        pass
    _broadcast_sync({"type": "engine_set", "engine": req.engine})
    return {"status": "ok", "engine": req.engine}


@app.post("/api/voice/test")
async def test_voice() -> dict:
    """Testa a voz atual com uma frase."""
    brain = get_brain()
    try:
        # Tenta falar uma frase de teste
        if hasattr(brain, 'speak'):
            await brain.speak("Olá! Eu sou a Shaz. Teste de voz completo.")
        return {"status": "ok", "message": "Voz testada"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/start")
async def voice_start():
    """Ativa o modo de voz (STT + TTS em loop)."""
    brain = get_brain()
    try:
        if brain.is_voice_active:
            return {"status": "ok", "message": "Voz já está ativa"}
        
        # Inicia o loop de voz em background
        _broadcast_sync({"type": "status", "status": "listening"})
        logger.info("[Voice] Modo de voz ativado via API")
        
        # Cria task para o loop de voz
        asyncio.ensure_future(brain.process_voice())
        
        return {"status": "ok", "message": "Modo de voz ativado"}
    except Exception as e:
        logger.error(f"[Voice] Erro ao ativar voz: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/stop")
async def voice_stop():
    """Desativa o modo de voz."""
    brain = get_brain()
    try:
        brain.stop_voice_mode()
        _broadcast_sync({"type": "status", "status": "online"})
        logger.info("[Voice] Modo de voz desativado via API")
        return {"status": "ok", "message": "Modo de voz desativado"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/voice/stop_speaking")
async def voice_stop_speaking():
    """Para a fala imediatamente sem desativar o modo de voz."""
    brain = get_brain()
    try:
        # Para o player de áudio
        if hasattr(brain, '_audio') and brain._audio:
            brain._audio.player.stop()
        
        # Limpa a fila de fala pendente
        if hasattr(brain, '_speak_queue') and brain._speak_queue:
            while not brain._speak_queue.empty():
                try:
                    brain._speak_queue.get_nowait()
                except:
                    pass
        
        # Se tiver worker, marca todas como done
        if hasattr(brain, '_speak_queue'):
            for _ in range(brain._speak_queue.qsize()):
                try:
                    brain._speak_queue.task_done()
                except:
                    pass
        
        _broadcast_sync({"type": "speaking_stopped"})
        logger.info("[Voice] Fala interrompida pelo usuario")
        return {"status": "ok", "message": "Fala interrompida"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/voice/status")
async def voice_status():
    """Retorna o status do modo de voz."""
    brain = get_brain()
    return {
        "voice_active": brain.is_voice_active if hasattr(brain, 'is_voice_active') else False
    }


@app.post("/api/personality/prompt")
async def set_system_prompt(req: PromptRequest) -> dict:
    """Atualiza o system prompt da personalidade."""
    try:
        brain = get_brain()
        personality = brain.personality if hasattr(brain, 'personality') else None
        if personality and hasattr(personality, 'set_system_prompt'):
            personality.set_system_prompt(req.prompt)
        else:
            # Fallback: guarda no custom prompt do server
            logger.info(f"[Server] System prompt atualizado ({len(req.prompt)} chars)")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/status")
async def system_status() -> dict:
    """Status completo do sistema."""
    brain = get_brain()
    try:
        stats = brain.get_stats() if hasattr(brain, 'get_stats') else {}
        voice_active = brain.is_voice_active if hasattr(brain, 'is_voice_active') else False
        config = brain.config if hasattr(brain, 'config') else None
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
        "tts_engines": stats.get("tts_engines", []),
        "language": config.language if (config and hasattr(config, 'language')) else "pt-BR",
        "version": "3.0.0",
    }


# ─── WebSocket ────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket para comunicação em tempo real."""
    await ws.accept()
    _ws_clients.append(ws)
    logger.info(f"[WS] Cliente conectado ({len(_ws_clients)} total)")
    
    try:
        # Envia status inicial
        await ws.send_text(json.dumps({
            "type": "connected",
            "message": "Conectado ao Shaz AI NEXUS v3.0",
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
                # Processa mensagem
                text = msg.get("message", "").strip()
                if not text:
                    continue
                
                brain = get_brain()
                response = await brain.process_message(text)
                
                await ws.send_text(json.dumps({
                    "type": "response",
                    "response": response,
                    "user": text,
                }))
            
            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
            
            elif msg_type == "clear":
                brain = get_brain()
                if hasattr(brain, 'clear_history'):
                    brain.clear_history()
                await ws.send_text(json.dumps({"type": "cleared"}))
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
    finally:
        try:
            _ws_clients.remove(ws)
        except ValueError:
            pass
        logger.info(f"[WS] Cliente desconectado ({len(_ws_clients)} restantes)")


# ─── Sirve o HTML diretamente ────────────────────────────────────────────
_html_path = _root / "shaz-terminal.html"

@app.get("/app")
async def serve_html():
    """Serve o shaz-terminal.html."""
    if _html_path.exists():
        return FileResponse(str(_html_path))
    return JSONResponse(
        status_code=404,
        content={"error": "shaz-terminal.html not found"},
    )


# ─── Run ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SHAZ_PORT", 8765))
    host = os.environ.get("SHAZ_HOST", "0.0.0.0")
    
    print(f"╔══════════════════════════════════════════════════╗")
    print(f"║     Shaz AI — NEXUS v3.0 — HTTP Server          ║")
    print(f"╠══════════════════════════════════════════════════╣")
    print(f"║  API:   http://localhost:{port}/api              ║")
    print(f"║  App:   http://localhost:{port}/app              ║")
    print(f"║  WS:    ws://localhost:{port}/ws                 ║")
    print(f"║  Docs:  http://localhost:{port}/docs             ║")
    print(f"╚══════════════════════════════════════════════════╝")
    
    uvicorn.run(app, host=host, port=port, log_level="info")