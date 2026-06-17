"""
apis/tavily/service.py
Serviço de busca web via Tavily com limpeza de resultados.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from apis.tavily.client import TavilyClient
from logs.logger import get_module_logger

log = get_module_logger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    score: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResult":
        return cls(
            title=data.get("title", ""),
            url=data.get("url", ""),
            snippet=data.get("content", "")[:400],
            score=data.get("score", 0.0),
        )


@dataclass
class SearchResponse:
    query: str
    answer: str
    results: list[SearchResult]

    def to_context(self, max_results: int = 3) -> str:
        """Formata resultados para uso como contexto do LLM."""
        lines = []
        if self.answer:
            lines.append(f"Resposta direta: {self.answer}\n")
        lines.append("Fontes relevantes:")
        for r in self.results[:max_results]:
            lines.append(f"- [{r.title}]({r.url})\n  {r.snippet}")
        return "\n".join(lines)


class TavilyService:
    """Serviço de pesquisa web para o agente de pesquisa."""

    def __init__(self, api_key: str) -> None:
        self._client = TavilyClient(api_key)

    async def search(self, query: str, max_results: int = 5) -> SearchResponse:
        """Executa uma pesquisa e retorna resultados estruturados."""
        raw = await self._client.search(query, max_results=max_results)
        results = [SearchResult.from_dict(r) for r in raw.get("results", [])]
        log.info(f"Tavily search: '{query}' → {len(results)} results")
        return SearchResponse(
            query=query,
            answer=raw.get("answer", ""),
            results=results,
        )

    async def close(self) -> None:
        await self._client.close()
