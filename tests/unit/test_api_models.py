"""
tests/unit/test_api_models.py
Testes para os modelos das APIs externas.
"""
from __future__ import annotations

import pytest


def test_github_repo_from_dict():
    from apis.github.models import GitHubRepo

    data = {
        "name": "shaz-ai",
        "full_name": "LucasY4N/shaz-ai",
        "description": "AI assistant",
        "html_url": "https://github.com/LucasY4N/shaz-ai",
        "stargazers_count": 42,
        "forks_count": 7,
        "language": "Python",
        "open_issues_count": 3,
        "default_branch": "main",
        "topics": ["ai", "python"],
    }
    repo = GitHubRepo.from_dict(data)

    assert repo.name == "shaz-ai"
    assert repo.stars == 42
    assert repo.language == "Python"
    assert "ai" in repo.topics


def test_github_commit_from_dict():
    from apis.github.models import GitHubCommit

    data = {
        "sha": "abc1234567890",
        "commit": {
            "message": "fix: corrige bug no TTS\n\nDetalhes do fix.",
            "author": {"name": "Lucas", "date": "2026-06-11T10:00:00Z"},
        },
        "html_url": "https://github.com/...",
    }
    commit = GitHubCommit.from_dict(data)

    assert commit.sha == "abc1234"           # truncado em 7
    assert commit.message == "fix: corrige bug no TTS"   # só primeira linha
    assert commit.author == "Lucas"


def test_weather_data_from_dict():
    from apis.weather.models import WeatherData

    data = {
        "name": "Manaus",
        "sys": {"country": "BR"},
        "main": {"temp": 305.15, "feels_like": 311.15, "humidity": 85},
        "weather": [{"description": "chuva moderada", "icon": "10d"}],
        "wind": {"speed": 2.5},
        "visibility": 9000,
    }
    w = WeatherData.from_dict(data)

    assert w.city == "Manaus"
    assert w.temperature == 32.0   # 305.15 - 273.15
    assert w.humidity == 85
    assert "Manaus" in w.to_text()
    assert "32.0°C" in w.to_text()


def test_search_result_from_dict():
    from apis.tavily.service import SearchResult

    data = {
        "title": "Python asyncio Guide",
        "url": "https://docs.python.org/asyncio",
        "content": "asyncio is a library to write concurrent code " * 20,
        "score": 0.95,
    }
    r = SearchResult.from_dict(data)

    assert r.title == "Python asyncio Guide"
    assert len(r.snippet) <= 400   # truncado
    assert r.score == 0.95


def test_search_response_to_context():
    from apis.tavily.service import SearchResponse, SearchResult

    results = [
        SearchResult("Title 1", "https://example.com/1", "Snippet 1", 0.9),
        SearchResult("Title 2", "https://example.com/2", "Snippet 2", 0.8),
    ]
    resp = SearchResponse(query="test", answer="Resposta direta aqui.", results=results)
    context = resp.to_context(max_results=2)

    assert "Resposta direta aqui." in context
    assert "Title 1" in context
    assert "example.com/1" in context
