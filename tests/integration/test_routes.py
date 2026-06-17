"""
tests/integration/test_routes.py
Testes de integração para as rotas do backend com TestClient.
Usa mocks para Brain e serviços externos.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_state():
    """Estado mockado para os testes de integração."""
    mock_brain = MagicMock()
    mock_brain.process_message = AsyncMock(return_value="Resposta de teste!")
    mock_brain.is_voice_active = False
    mock_brain.api = MagicMock()
    mock_brain.api.current_provider = "gemini"
    mock_brain.api.available_providers = ["gemini", "groq"]
    mock_brain.clear_history = MagicMock()
    mock_brain.get_stats = MagicMock(return_value={
        "current_provider": "gemini",
        "providers": ["gemini"],
        "voice_active": False,
        "memory": 5,
    })

    return {
        "brain": mock_brain,
        "weather_service": None,
        "tavily_service": None,
        "github_service": None,
        "wikipedia_service": None,
        "coding_agent": None,
        "stats": {"messages": 0, "tokens": 0},
    }


@pytest.fixture
def client(mock_state):
    """TestClient com estado mockado injetado."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    from backend.routes import chat as chat_route
    from backend.routes import stats as stats_route
    from backend.routes import tools as tools_route

    app.include_router(chat_route.register(mock_state), prefix="/api")
    app.include_router(stats_route.register(mock_state), prefix="/api")
    app.include_router(tools_route.register(mock_state), prefix="/api")

    return TestClient(app)


def test_chat_endpoint_returns_response(client, mock_state):
    resp = client.post("/api/chat", json={"message": "Olá!"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Resposta de teste!"
    assert data["tokens"] > 0


def test_chat_endpoint_rejects_empty_message(client):
    resp = client.post("/api/chat", json={"message": ""})
    assert resp.status_code == 422   # Pydantic validation error


def test_chat_clear_endpoint(client):
    resp = client.post("/api/chat/clear")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stats_endpoint(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert "tokens" in data
    assert "providers" in data


def test_tools_weather_without_service(client):
    resp = client.post("/api/tools/weather", json={"city": "Manaus"})
    assert resp.status_code == 503
    assert "OPENWEATHER_API_KEY" in resp.json()["detail"]


def test_tools_search_without_service(client):
    resp = client.post("/api/tools/search", json={"query": "Python 2026"})
    assert resp.status_code == 503
    assert "TAVILY_API_KEY" in resp.json()["detail"]
