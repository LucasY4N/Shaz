"""
backend/routes/voice.py
Rotas do sistema de voz: TTS, STT, configuração de engine.
"""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException
from backend.schemas.requests import VoiceRequest, EngineRequest
from backend.schemas.responses import ActionResponse
from logs.logger import get_module_logger

log = get_module_logger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])


def register(app_state: dict):

    @router.post("/set", response_model=ActionResponse)
    async def set_voice(req: VoiceRequest) -> ActionResponse:
        brain = app_state.get("brain")
        if brain and hasattr(brain, "_tts") and hasattr(brain._tts, "_synthesizers"):
            edge = brain._tts._synthesizers.get("edge")
            if edge:
                edge._voice = req.voice
        return ActionResponse(status="ok", message=f"Voz alterada: {req.voice}")

    @router.post("/engine", response_model=ActionResponse)
    async def set_engine(req: EngineRequest) -> ActionResponse:
        brain = app_state.get("brain")
        if brain and hasattr(brain, "_tts"):
            brain._tts.set_engine(req.engine)
        return ActionResponse(status="ok", message=f"Engine TTS: {req.engine}")

    @router.post("/test", response_model=ActionResponse)
    async def test_voice() -> ActionResponse:
        brain = app_state.get("brain")
        if not brain:
            raise HTTPException(503, detail="Brain não disponível")
        try:
            await brain.speak("Olá! Eu sou a Shaz. Sistema de voz funcionando corretamente.")
            return ActionResponse(status="ok", message="Voz testada com sucesso")
        except Exception as e:
            return ActionResponse(status="error", message=str(e))

    @router.post("/start", response_model=ActionResponse)
    async def start_voice() -> ActionResponse:
        brain = app_state.get("brain")
        if not brain:
            raise HTTPException(503, detail="Brain não disponível")
        if brain.is_voice_active:
            return ActionResponse(status="ok", message="Voz já ativa")
        asyncio.ensure_future(brain.process_voice())
        return ActionResponse(status="ok", message="Modo de voz ativado")

    @router.post("/stop", response_model=ActionResponse)
    async def stop_voice() -> ActionResponse:
        brain = app_state.get("brain")
        if brain and hasattr(brain, "stop_voice_mode"):
            brain.stop_voice_mode()
        return ActionResponse(status="ok", message="Modo de voz desativado")

    @router.post("/stop_speaking", response_model=ActionResponse)
    async def stop_speaking() -> ActionResponse:
        brain = app_state.get("brain")
        if brain:
            if hasattr(brain, "_audio") and brain._audio:
                brain._audio.player.stop()
            if hasattr(brain, "_speak_queue") and brain._speak_queue:
                while not brain._speak_queue.empty():
                    try:
                        brain._speak_queue.get_nowait()
                    except Exception:
                        pass
        return ActionResponse(status="ok", message="Fala interrompida")

    @router.get("/status")
    async def voice_status() -> dict:
        brain = app_state.get("brain")
        return {"voice_active": brain.is_voice_active if brain else False}

    return router
