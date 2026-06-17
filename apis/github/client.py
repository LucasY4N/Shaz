"""
apis/github/client.py
Cliente HTTP para a API do GitHub REST v3.
Responsável apenas por chamadas HTTP puras.
"""
from __future__ import annotations

from typing import Any

import httpx

from logs.logger import get_module_logger

log = get_module_logger(__name__)

GITHUB_BASE_URL = "https://api.github.com"


class GitHubClient:
    """Cliente baixo nível para a API REST do GitHub."""

    def __init__(self, token: str = "") -> None:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._http = httpx.AsyncClient(
            base_url=GITHUB_BASE_URL,
            headers=headers,
            timeout=15.0,
        )
        self._authenticated = bool(token)
        log.info(f"GitHubClient initialized (authenticated={self._authenticated})")

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET genérico."""
        resp = await self._http.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()
