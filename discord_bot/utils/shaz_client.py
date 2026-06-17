"""
discord_bot/utils/shaz_client.py
Cliente HTTP que conecta o bot Discord ao backend da Shaz (run_server_new.py).

O bot Discord NÃO importa o Brain diretamente.
Toda a inteligência vem via API HTTP — arquitetura limpa e desacoplada.
"""
from __future__ import annotations

from typing import Any, Optional

import httpx

from discord_bot.utils.logger import log


class ShazClient:
    """
    Cliente para a API REST do Shaz AI.
    Encapsula todas as chamadas HTTP do bot para o backend.
    """

    def __init__(self, base_url: str = "http://localhost:8765", timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._http = httpx.AsyncClient(timeout=timeout)
        log.info(f"ShazClient conectado em {self._base}")

    # ── Chat ──────────────────────────────────────────────────────────────

    async def chat(self, message: str) -> str:
        """Envia mensagem para a Shaz e retorna a resposta."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/chat",
                json={"message": message},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "Não consegui processar sua mensagem.")
        except httpx.ConnectError:
            log.error("Backend Shaz offline — não foi possível conectar")
            return "Estou com dificuldades para me conectar ao meu cérebro agora... tenta de novo em instantes!"
        except Exception as e:
            log.error(f"chat() error: {e}")
            return f"Ocorreu um erro: {e}"

    # ── Ferramentas ───────────────────────────────────────────────────────

    async def get_weather(self, city: str) -> dict[str, Any]:
        """Retorna clima atual de uma cidade."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/tools/weather",
                json={"city": city},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def search_web(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Pesquisa na web via Tavily."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/tools/search",
                json={"query": query, "max_results": max_results},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def search_wikipedia(self, topic: str) -> dict[str, Any]:
        """Busca resumo no Wikipedia."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/tools/wikipedia",
                json={"query": topic},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def analyze_github(self, owner: str, repo: str) -> dict[str, Any]:
        """Analisa repositório GitHub."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/tools/github/repo",
                json={"owner": owner, "repo": repo},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def diagnose_error(self, error: str, code: str = "", language: str = "python") -> dict[str, Any]:
        """Diagnostica um erro de código."""
        try:
            resp = await self._http.post(
                f"{self._base}/api/tools/diagnose",
                json={"error": error, "code": code, "language": language},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Status ────────────────────────────────────────────────────────────

    async def get_status(self) -> dict[str, Any]:
        """Retorna status do sistema Shaz."""
        try:
            resp = await self._http.get(f"{self._base}/api/stats/status")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"online": False, "error": str(e)}

    async def is_online(self) -> bool:
        """Verifica se o backend está disponível."""
        try:
            resp = await self._http.get(f"{self._base}/", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    # ── TTS para voz no Discord ───────────────────────────────────────────

    async def synthesize_voice(self, text: str) -> Optional[bytes]:
        """
        Sintetiza texto em áudio via backend.
        Retorna bytes de áudio WAV/MP3 para tocar no canal de voz.
        """
        try:
            resp = await self._http.post(
                f"{self._base}/api/voice/synthesize",
                json={"text": text},
                timeout=15.0,
            )
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith(("audio/", "application/octet")):
                return resp.content
            return None
        except Exception as e:
            log.error(f"synthesize_voice() error: {e}")
            return None

    async def close(self) -> None:
        await self._http.aclose()
