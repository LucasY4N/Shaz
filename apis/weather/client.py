"""
apis/weather/client.py
Cliente para OpenWeatherMap API.
"""
from __future__ import annotations
import httpx
from logs.logger import get_module_logger

log = get_module_logger(__name__)
OWM_BASE = "https://api.openweathermap.org/data/2.5"


class WeatherClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(timeout=10.0)

    async def get(self, path: str, params: dict) -> dict:
        params["appid"] = self._api_key
        params["lang"] = "pt_br"
        resp = await self._http.get(f"{OWM_BASE}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._http.aclose()
