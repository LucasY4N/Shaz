"""
discord_bot/tests/test_bot.py
Testes unitários do bot Discord com mocks.
Não precisa de token real nem conexão com Discord.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── ShazClient ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shaz_client_chat_returns_response():
    """ShazClient.chat() deve retornar resposta do backend."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"response": "Olá! Como posso ajudar?", "tokens": 10}
        mock_post.return_value = mock_resp

        from discord_bot.utils.shaz_client import ShazClient
        client = ShazClient()
        result = await client.chat("Oi!")
        assert result == "Olá! Como posso ajudar?"


@pytest.mark.asyncio
async def test_shaz_client_chat_handles_connection_error():
    """ShazClient.chat() deve retornar msg amigável quando backend offline."""
    import httpx
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("refused")):
        from discord_bot.utils.shaz_client import ShazClient
        client = ShazClient()
        result = await client.chat("Oi!")
        assert "dificuldades" in result.lower() or "erro" in result.lower()


@pytest.mark.asyncio
async def test_shaz_client_is_online_true():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        from discord_bot.utils.shaz_client import ShazClient
        client = ShazClient()
        assert await client.is_online() is True


@pytest.mark.asyncio
async def test_shaz_client_is_online_false():
    import httpx
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("refused")):
        from discord_bot.utils.shaz_client import ShazClient
        client = ShazClient()
        assert await client.is_online() is False


# ── Helpers ───────────────────────────────────────────────────────────────

def test_truncate_short_text():
    from discord_bot.utils.helpers import truncate
    assert truncate("texto curto") == "texto curto"


def test_truncate_long_text():
    from discord_bot.utils.helpers import truncate
    long_text = "a" * 2100
    result = truncate(long_text, 1900)
    assert len(result) <= 1900
    assert result.endswith("...")


def test_weather_embed_structure():
    import discord
    from discord_bot.utils.helpers import weather_embed

    data = {
        "status": "ok",
        "data": {
            "city": "Manaus",
            "country": "BR",
            "temperature": 32.1,
            "feels_like": 38.0,
            "humidity": 85,
            "description": "chuva moderada",
            "wind_speed": 2.5,
        },
    }
    embed = weather_embed(data)
    assert isinstance(embed, discord.Embed)
    assert "Manaus" in embed.title
    assert len(embed.fields) >= 3


def test_github_embed_structure():
    import discord
    from discord_bot.utils.helpers import github_embed

    data = {
        "status": "ok",
        "data": {
            "repository": {
                "name": "shaz-ai",
                "description": "AI Assistant",
                "url": "https://github.com/test/shaz",
                "language": "Python",
                "stars": 42,
                "forks": 7,
                "open_issues": 3,
                "topics": ["ai"],
            },
            "recent_commits": [
                {"sha": "abc1234", "message": "fix bug", "author": "Lucas", "date": "2026-01-01"},
            ],
            "open_issues": [],
        },
    }
    embed = github_embed(data)
    assert isinstance(embed, discord.Embed)
    assert "shaz-ai" in embed.title


# ── OnMessage logic ───────────────────────────────────────────────────────

def test_on_message_split_response_short():
    """Mensagens curtas não devem ser divididas."""
    # Simula a lógica de split sem instanciar o Cog completo
    def split(text, limit=1900):
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            cut = text.rfind("\n", 0, limit)
            if cut == -1:
                cut = limit
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()
        return chunks

    result = split("Resposta curta da Shaz!")
    assert result == ["Resposta curta da Shaz!"]


def test_on_message_split_response_long():
    """Mensagens longas devem ser divididas em chunks."""
    def split(text, limit=1900):
        if len(text) <= limit:
            return [text]
        chunks = []
        while text:
            if len(text) <= limit:
                chunks.append(text)
                break
            cut = text.rfind("\n", 0, limit)
            if cut == -1:
                cut = limit
            chunks.append(text[:cut].strip())
            text = text[cut:].strip()
        return chunks

    long_text = "linha\n" * 500   # 3000 chars
    result = split(long_text)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk) <= 1900
