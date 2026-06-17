"""
backend/routes/chat.py
Rotas de chat — sem lógica de negócio, apenas delegação ao agente.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from backend.schemas.requests import ChatRequest
from backend.schemas.responses import ChatResponse
from logs.logger import get_module_logger

log = get_module_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def register(app_state: dict):
    """Registra as rotas com acesso ao estado compartilhado."""

    @router.post("", response_model=ChatResponse)
    async def send_message(req: ChatRequest) -> ChatResponse:
        """Processa uma mensagem e retorna a resposta da Shaz."""
        brain = app_state.get("brain")
        if not brain:
            raise HTTPException(503, detail="Sistema não inicializado")

        response = await brain.process_message(req.message)
        stats = app_state.get("stats", {})
        stats["messages"] = stats.get("messages", 0) + 1
        stats["tokens"] = stats.get("tokens", 0) + len(req.message) + len(response)

        return ChatResponse(
            response=response,
            tokens=stats["tokens"],
            provider=brain.api.current_provider if hasattr(brain, "api") else "",
        )

    @router.post("/clear")
    async def clear_history() -> dict:
        brain = app_state.get("brain")
        if brain and hasattr(brain, "clear_history"):
            brain.clear_history()
        stats = app_state.get("stats", {})
        stats["messages"] = 0
        return {"status": "ok", "message": "Histórico limpo"}

    return router
