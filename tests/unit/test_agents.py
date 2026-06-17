"""
tests/unit/test_agents.py
Testes unitários para os agentes com mocks.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock


# ── ChatAgent ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_agent_respond():
    """ChatAgent deve delegar ao brain.process_message."""
    from agents.chat_agent import ChatAgent

    mock_brain = MagicMock()
    mock_brain.process_message = AsyncMock(return_value="Olá! Como posso ajudar?")

    agent = ChatAgent(mock_brain)
    result = await agent.respond("Oi!")

    assert result == "Olá! Como posso ajudar?"
    mock_brain.process_message.assert_called_once_with("Oi!")


# ── CodingAgent ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coding_agent_diagnose_parses_json():
    """CodingAgent deve parsear JSON válido da resposta do LLM."""
    from agents.coding_agent import CodingAgent

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=(
        '{"error_type":"TypeError","root_cause":"x é None",'
        '"patch":"if x: ...","explanation":"Variável não inicializada.","references":[]}'
    ))

    agent = CodingAgent(mock_llm)
    result = await agent.diagnose("TypeError: NoneType")

    assert result.error_type == "TypeError"
    assert result.root_cause == "x é None"
    assert result.patch == "if x: ..."


@pytest.mark.asyncio
async def test_coding_agent_diagnose_handles_invalid_json():
    """CodingAgent deve lidar com resposta não-JSON."""
    from agents.coding_agent import CodingAgent

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value="Resposta sem JSON aqui.")

    agent = CodingAgent(mock_llm)
    result = await agent.diagnose("SomeError")

    assert result.error_type == "unknown"
    assert "Resposta sem JSON" in result.root_cause


# ── MemoryAgent ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_memory_agent_saves_preference():
    """MemoryAgent deve detectar e salvar preferência quando trigger presente."""
    from agents.memory_agent import MemoryAgent

    mock_memory = MagicMock()
    mock_memory.save_memory = MagicMock()

    agent = MemoryAgent(mock_memory)
    count = await agent.extract_and_save("meu nome é Lucas", "Olá Lucas!", "user_1")

    assert count >= 1
    # Deve ter salvo pelo menos 1 "preference"
    calls = mock_memory.save_memory.call_args_list
    types = [c.kwargs.get("memory_type", c.args[1] if len(c.args) > 1 else "") for c in calls]
    assert "preference" in types


@pytest.mark.asyncio
async def test_memory_agent_no_preference_trigger():
    """MemoryAgent não deve salvar preference em mensagem genérica."""
    from agents.memory_agent import MemoryAgent

    mock_memory = MagicMock()
    mock_memory.save_memory = MagicMock()

    agent = MemoryAgent(mock_memory)
    count = await agent.extract_and_save("como está o tempo hoje?", "Está ensolarado!", "user_1")

    calls = mock_memory.save_memory.call_args_list
    types = [c.kwargs.get("memory_type", "") for c in calls]
    assert "preference" not in types


# ── SystemAgent ────────────────────────────────────────────────────────────

def test_system_agent_get_service_status():
    """SystemAgent deve reportar corretamente serviços None vs instanciados."""
    from agents.system_agent import SystemAgent

    agent = SystemAgent()
    mock_service = MagicMock()

    status = agent.get_service_status({
        "weather": mock_service,
        "tavily": None,
        "github": mock_service,
        "wikipedia": None,
    })

    assert status["weather"] == "ok"
    assert status["tavily"] == "not_configured"
    assert status["github"] == "ok"
    assert status["wikipedia"] == "not_configured"
