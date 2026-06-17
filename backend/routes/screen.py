"""
backend/routes/screen.py
Rotas para controle do monitoramento de tela.
"""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.schemas.responses import ActionResponse
from logs.logger import get_module_logger

log = get_module_logger(__name__)
router = APIRouter(prefix="/screen", tags=["Screen Watcher"])


class ScreenConfig(BaseModel):
    interval_seconds: float = 30.0
    monitor_index: int = 0
    speak: bool = True
    save_screenshots: bool = False


def register(app_state: dict):

    @router.post("/start", response_model=ActionResponse)
    async def start_watcher(config: ScreenConfig) -> ActionResponse:
        """Ativa o monitoramento de tela da Shaz."""
        brain = app_state.get("brain")
        if not brain:
            raise HTTPException(503, detail="Brain não disponível")

        watcher = app_state.get("screen_watcher")
        if watcher and watcher.is_running:
            return ActionResponse(status="ok", message="Monitoramento já está ativo")

        try:
            from shaz.services.screen_watcher import ScreenWatcher

            def on_comment(text: str):
                # Notifica WebSocket clients via broadcast
                broadcast_fn = app_state.get("broadcast")
                if broadcast_fn:
                    asyncio.ensure_future(broadcast_fn({
                        "type": "screen_comment",
                        "comment": text,
                    }))

            watcher = ScreenWatcher(
                brain=brain,
                interval_seconds=config.interval_seconds,
                monitor_index=config.monitor_index,
                speak=config.speak,
                save_screenshots=config.save_screenshots,
                on_comment=on_comment,
            )
            app_state["screen_watcher"] = watcher
            await watcher.start()

            return ActionResponse(
                status="ok",
                message=f"Monitoramento ativado — observando a cada {config.interval_seconds}s",
            )
        except RuntimeError as e:
            raise HTTPException(503, detail=str(e))
        except Exception as e:
            raise HTTPException(500, detail=f"Erro ao iniciar: {e}")

    @router.post("/stop", response_model=ActionResponse)
    async def stop_watcher() -> ActionResponse:
        """Desativa o monitoramento de tela."""
        watcher = app_state.get("screen_watcher")
        if not watcher or not watcher.is_running:
            return ActionResponse(status="ok", message="Monitoramento já estava inativo")

        await watcher.stop()
        return ActionResponse(status="ok", message="Monitoramento desativado")

    @router.post("/observe", response_model=ActionResponse)
    async def observe_now() -> ActionResponse:
        """Faz uma observação imediata da tela (sem esperar o intervalo)."""
        brain = app_state.get("brain")
        if not brain:
            raise HTTPException(503, detail="Brain não disponível")

        watcher = app_state.get("screen_watcher")

        # Cria um watcher temporário se não existir
        if not watcher:
            from shaz.services.screen_watcher import ScreenWatcher
            watcher = ScreenWatcher(brain=brain, interval_seconds=999999, speak=True)

        try:
            obs = await watcher.observe_once()
            if obs:
                return ActionResponse(status="ok", message=obs.comment, data={
                    "comment": obs.comment,
                    "observation_count": watcher.observation_count,
                })
            return ActionResponse(status="error", message="Não foi possível capturar a tela")
        except Exception as e:
            raise HTTPException(500, detail=str(e))

    @router.get("/status")
    async def watcher_status() -> dict:
        """Retorna o status atual do monitoramento."""
        watcher = app_state.get("screen_watcher")
        if not watcher:
            return {"active": False, "observations": 0, "interval_seconds": None}
        return {
            "active": watcher.is_running,
            "observations": watcher.observation_count,
            "interval_seconds": watcher._interval,
        }

    @router.post("/interval", response_model=ActionResponse)
    async def set_interval(seconds: float) -> ActionResponse:
        """Altera o intervalo entre observações sem reiniciar."""
        watcher = app_state.get("screen_watcher")
        if not watcher:
            raise HTTPException(404, detail="Watcher não iniciado")
        watcher.set_interval(seconds)
        return ActionResponse(status="ok", message=f"Intervalo alterado para {seconds}s")

    return router
