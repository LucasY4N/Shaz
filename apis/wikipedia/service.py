"""
apis/wikipedia/service.py
Integração com Wikipedia para busca de conhecimento.
Usa a API REST pública do Wikipedia — sem chave necessária.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from config.constants import WIKIPEDIA_CACHE_TTL
from logs.logger import get_module_logger

log = get_module_logger(__name__)


@dataclass
class WikiArticle:
    title: str
    summary: str
    url: str
    categories: list[str]

    def to_context(self) -> str:
        return f"**{self.title}** ({self.url})\n{self.summary}"


class WikipediaService:
    """Busca e resumos do Wikipedia em português e inglês."""

    PT_API = "https://pt.wikipedia.org/api/rest_v1"
    EN_API = "https://en.wikipedia.org/api/rest_v1"

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(timeout=15.0)
        self._cache: dict[str, tuple[WikiArticle, float]] = {}

    async def summary(self, topic: str, lang: str = "pt") -> WikiArticle:
        """Retorna o resumo de um artigo do Wikipedia."""
        key = f"{lang}:{topic.lower()}"
        if key in self._cache:
            article, ts = self._cache[key]
            if time.time() - ts < WIKIPEDIA_CACHE_TTL:
                return article

        base = self.PT_API if lang == "pt" else self.EN_API
        safe_topic = topic.replace(" ", "_")
        resp = await self._http.get(f"{base}/page/summary/{safe_topic}")

        if resp.status_code == 404 and lang == "pt":
            log.info(f"Wikipedia PT not found for '{topic}', trying EN")
            return await self.summary(topic, lang="en")

        resp.raise_for_status()
        data = resp.json()

        article = WikiArticle(
            title=data.get("title", topic),
            summary=data.get("extract", "")[:800],
            url=data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            categories=[],
        )
        self._cache[key] = (article, time.time())
        log.info(f"Wikipedia fetched: '{topic}' ({lang})")
        return article

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Busca artigos por termo."""
        resp = await self._http.get(
            "https://pt.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": limit,
                "format": "json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        titles = data[1] if len(data) > 1 else []
        urls = data[3] if len(data) > 3 else []
        return [
            {"title": t, "url": u}
            for t, u in zip(titles, urls)
        ]

    async def close(self) -> None:
        await self._http.aclose()
