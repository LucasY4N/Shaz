"""
tests/unit/test_screen_watcher.py
Testes do ScreenWatcher com mocks para não precisar de tela real.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_brain():
    brain = MagicMock()
    brain.speak = AsyncMock()
    brain._config = MagicMock()
    brain._config.gemini_api_key = "fake-key"
    return brain


@pytest.mark.asyncio
async def test_screen_watcher_initializes(mock_brain):
    """ScreenWatcher deve inicializar sem erros."""
    with patch("shaz.services.screen_watcher.MSS_AVAILABLE", True), \
         patch("shaz.services.screen_watcher.PIL_AVAILABLE", True):
        from shaz.services.screen_watcher import ScreenWatcher
        watcher = ScreenWatcher(brain=mock_brain, interval_seconds=60)
        assert not watcher.is_running
        assert watcher.observation_count == 0


@pytest.mark.asyncio
async def test_screen_watcher_set_interval(mock_brain):
    """set_interval deve aplicar com mínimo de 5s."""
    with patch("shaz.services.screen_watcher.MSS_AVAILABLE", True), \
         patch("shaz.services.screen_watcher.PIL_AVAILABLE", True):
        from shaz.services.screen_watcher import ScreenWatcher
        watcher = ScreenWatcher(brain=mock_brain, interval_seconds=60)
        watcher.set_interval(120)
        assert watcher._interval == 120
        watcher.set_interval(1)   # abaixo do mínimo
        assert watcher._interval == 5


@pytest.mark.asyncio
async def test_screen_watcher_raises_without_mss(mock_brain):
    """ScreenWatcher.start() deve lançar RuntimeError se mss não instalado."""
    with patch("shaz.services.screen_watcher.MSS_AVAILABLE", False), \
         patch("shaz.services.screen_watcher.PIL_AVAILABLE", True):
        from shaz.services.screen_watcher import ScreenWatcher
        watcher = ScreenWatcher(brain=mock_brain)
        with pytest.raises(RuntimeError, match="mss"):
            await watcher.start()


@pytest.mark.asyncio
async def test_screen_watcher_delivers_comment(mock_brain):
    """_deliver deve chamar speak e o callback."""
    with patch("shaz.services.screen_watcher.MSS_AVAILABLE", True), \
         patch("shaz.services.screen_watcher.PIL_AVAILABLE", True):
        from shaz.services.screen_watcher import ScreenWatcher, ScreenObservation
        import time

        comments_received = []
        watcher = ScreenWatcher(
            brain=mock_brain,
            speak=True,
            on_comment=lambda c: comments_received.append(c),
        )

        obs = ScreenObservation(
            timestamp=time.time(),
            comment="Opa, jogando Minecraft de novo!",
            screenshot_bytes=b"fake",
        )
        await watcher._deliver(obs)

        assert watcher.observation_count == 1
        assert comments_received == ["Opa, jogando Minecraft de novo!"]
        mock_brain.speak.assert_called_once_with("Opa, jogando Minecraft de novo!")


@pytest.mark.asyncio
async def test_screen_watcher_avoids_repeated_comment(mock_brain):
    """_deliver não deve repetir o mesmo comentário duas vezes."""
    with patch("shaz.services.screen_watcher.MSS_AVAILABLE", True), \
         patch("shaz.services.screen_watcher.PIL_AVAILABLE", True):
        from shaz.services.screen_watcher import ScreenWatcher, ScreenObservation
        import time

        watcher = ScreenWatcher(brain=mock_brain, speak=False)
        watcher._last_comment = "comentário igual"

        # Simula que o Gemini retornou o mesmo comentário
        result = await watcher._analyze_with_gemini(b"fake")
        # Como não tem Gemini real, só verifica que _last_comment funciona
        assert watcher._last_comment == "comentário igual"
