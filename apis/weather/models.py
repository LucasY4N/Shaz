"""
apis/weather/models.py
Modelos para dados de clima.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class WeatherData:
    city: str
    country: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    wind_speed: float
    visibility: int
    icon: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WeatherData":
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather = data.get("weather", [{}])[0]
        return cls(
            city=data.get("name", ""),
            country=data.get("sys", {}).get("country", ""),
            temperature=round(main.get("temp", 273.15) - 273.15, 1),
            feels_like=round(main.get("feels_like", 273.15) - 273.15, 1),
            humidity=main.get("humidity", 0),
            description=weather.get("description", ""),
            wind_speed=wind.get("speed", 0),
            visibility=data.get("visibility", 0),
            icon=weather.get("icon", ""),
        )

    def to_text(self) -> str:
        return (
            f"Clima em {self.city}, {self.country}: "
            f"{self.description.capitalize()}, "
            f"{self.temperature}°C (sensação {self.feels_like}°C), "
            f"umidade {self.humidity}%, "
            f"vento {self.wind_speed} m/s."
        )
