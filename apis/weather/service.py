"""
apis/weather/service.py
Serviço de clima com cache simples.
"""
from __future__ import annotations
import time
from apis.weather.client import WeatherClient
from apis.weather.models import WeatherData
from config.constants import WEATHER_CACHE_TTL
from logs.logger import get_module_logger

log = get_module_logger(__name__)


class WeatherService:
    def __init__(self, api_key: str) -> None:
        self._client = WeatherClient(api_key)
        self._cache: dict[str, tuple[WeatherData, float]] = {}

    async def get_current(self, city: str) -> WeatherData:
        """Retorna clima atual com cache de 10 minutos."""
        key = city.lower().strip()
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < WEATHER_CACHE_TTL:
                log.debug(f"Weather cache hit: {city}")
                return data

        raw = await self._client.get("/weather", {"q": city})
        weather = WeatherData.from_dict(raw)
        self._cache[key] = (weather, time.time())
        log.info(f"Weather fetched for {city}: {weather.temperature}°C")
        return weather

    async def get_forecast(self, city: str, days: int = 3) -> list[dict]:
        """Retorna previsão dos próximos dias."""
        raw = await self._client.get("/forecast", {"q": city, "cnt": days * 8})
        items = raw.get("list", [])
        # Agrupa por dia
        days_data: dict[str, list] = {}
        for item in items:
            day = item.get("dt_txt", "")[:10]
            days_data.setdefault(day, []).append(item)

        result = []
        for day, readings in list(days_data.items())[:days]:
            temps = [r["main"]["temp"] - 273.15 for r in readings]
            desc = readings[len(readings)//2]["weather"][0]["description"]
            result.append({
                "date": day,
                "min": round(min(temps), 1),
                "max": round(max(temps), 1),
                "description": desc,
            })
        return result

    async def close(self) -> None:
        await self._client.close()
