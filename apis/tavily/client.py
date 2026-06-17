"""
apis/tavily/client.py  |  apis/tavily/models.py  |  apis/tavily/service.py
Web search via Tavily API — pesquisa inteligente com resumos.
"""
from __future__ import annotations

import httpx
from logs.logger import get_module_logger

log = get_module_logger(__name__)


class TavilyClient:
    """Cliente HTTP para a API Tavily Search."""

    BASE_URL = "https://api.tavily.com"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=20.0,
        )

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
    ) -> dict:
        payload = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": False,
        }
        resp = await self._http.post("/search", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()
