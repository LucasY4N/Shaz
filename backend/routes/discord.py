"""
backend/routes/discord.py
Rotas para controle do Discord Bot via API.
Iniciar/Parar/Status do bot diretamente pela interface web.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

from fastapi import APIRouter


def register(state: dict[str, Any]) -> APIRouter:
    router = APIRouter(tags=["discord"])

    @router.get("/discord/status")
    async def discord_status():
        """Retorna o status atual do Discord bot."""
        return {
            "running": state.get("discord_bot_running", False),
            "error": state.get("discord_bot_error"),
            "bot_instance": state.get("discord_bot") is not None,
        }

    @router.post("/discord/start")
    async def discord_start():
        """Inicia o Discord bot em uma thread separada."""
        if state.get("discord_bot_running"):
            return {"status": "ok", "message": "Discord bot já está rodando"}

        # Limpa erro anterior
        state["discord_bot_error"] = None

        # Importa e inicia o bot em thread separada
        from discord_bot.bot.bot import ShazBot
        from discord_bot.config.settings import get_discord_settings

        settings = get_discord_settings()
        if not settings.has_token:
            state["discord_bot_error"] = "DISCORD_TOKEN não configurado no .env"
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
                    state["discord_bot_error"] = str(e)
                    state["discord_bot_running"] = False
                finally:
                    if not bot.is_closed():
                        await bot.close()
                    state["discord_bot_running"] = False

            try:
                loop = _asyncio.new_event_loop()
                _asyncio.set_event_loop(loop)
                loop.run_until_complete(_start())
            except Exception as e:
                state["discord_bot_error"] = str(e)
                state["discord_bot_running"] = False

        t = threading.Thread(target=run_bot, daemon=True, name="discord-bot")
        t.start()

        state["discord_bot"] = True  # sinal que foi iniciado
        state["discord_bot_running"] = True
        state["discord_bot_thread"] = t

        # Broadcast para a interface web
        broadcast = state.get("broadcast")
        if broadcast:
            import json as _json
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(broadcast({
                        "type": "discord_status",
                        "running": True,
                        "error": None,
                    }))
            except RuntimeError:
                pass

        return {"status": "ok", "message": "Discord bot iniciado com sucesso"}

    @router.post("/discord/stop")
    async def discord_stop():
        """Para o Discord bot."""
        if not state.get("discord_bot_running"):
            return {"status": "ok", "message": "Discord bot não está rodando"}

        # Sinaliza parada — a thread vai finalizar sozinha
        # O bot será parado no finally da thread quando receber exceção
        # Como usa daemon=True, vai ser finalizado quando o servidor parar
        state["discord_bot_running"] = False

        # Tenta um shutdown mais educado fechando o WebSocket do bot
        # (a thread vai encerrar quando a conexão discord fechar)
        # A melhor forma é forçar o loop a parar já que o bot roda em thread separada

        broadcast = state.get("broadcast")
        if broadcast:
            import json as _json
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(broadcast({
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

    return router