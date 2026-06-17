"""
backend/routes/stats.py
Rotas de estatísticas e status do sistema.
"""
from __future__ import annotations

from fastapi import APIRouter
from backend.schemas.responses import StatsResponse, StatusResponse
from logs.logger import get_module_logger

log = get_module_logger(__name__)
router = APIRouter(prefix="/stats", tags=["Stats"])


def register(app_state: dict):

    @router.get("", response_model=StatsResponse)
    async def get_stats() -> StatsResponse:
        stats = app_state.get("stats", {})
        brain = app_state.get("brain")

        brain_stats = {}
        if brain and hasattr(brain, "get_stats"):
            try:
                brain_stats = brain.get_stats()
            except Exception:
                pass

        return StatsResponse(
            messages=stats.get("messages", 0),
            tokens=stats.get("tokens", 0),
            memories=brain_stats.get("memory", 0),
            current_provider=brain_stats.get("current_provider", ""),
            providers=brain_stats.get("providers", []),
            voice_active=brain_stats.get("voice_active", False),
        )

    @router.get("/status", response_model=StatusResponse)
    async def get_status() -> StatusResponse:
        from config.settings import get_settings
        settings = get_settings()
        brain = app_state.get("brain")
        stats = app_state.get("stats", {})

        services = {
            "weather": "ok" if app_state.get("weather_service") else "not_configured",
            "tavily": "ok" if app_state.get("tavily_service") else "not_configured",
            "github": "ok" if app_state.get("github_service") else "not_configured",
            "wikipedia": "ok" if app_state.get("wikipedia_service") else "ok",  # sempre disponível
        }

        voice_active = False
        current_provider = ""
        available_providers: list[str] = []

        if brain:
            if hasattr(brain, "is_voice_active"):
                voice_active = brain.is_voice_active
            if hasattr(brain, "api"):
                current_provider = brain.api.current_provider
                available_providers = brain.api.available_providers

        return StatusResponse(
            version=settings.app_version,
            voice_active=voice_active,
            messages_session=stats.get("messages", 0),
            tokens_session=stats.get("tokens", 0),
            current_provider=current_provider,
            available_providers=available_providers,
            services=services,
        )

    return router
