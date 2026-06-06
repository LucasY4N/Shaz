"""
tests/test_chat_use_case.py
Testes unitários do ChatUseCase com mocks.
"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.use_cases.chat import ChatUseCase
from core.entities.models import Conversation, Memory, MemoryType


@pytest.fixture
def mock_llm() -> AsyncMock:
    llm = AsyncMock()
    llm.complete = AsyncMock(return_value="Olá! Como posso ajudar?")
    return llm


@pytest.fixture
def mock_memory() -> AsyncMock:
    mem = AsyncMock()
    mem.search = AsyncMock(return_value=[])
    mem.save = AsyncMock(return_value="mem-123")
    return mem


@pytest.fixture
def mock_conversations() -> AsyncMock:
    conv = AsyncMock()
    conv.get = AsyncMock(return_value=None)
    conv.save = AsyncMock(return_value="conv-123")
    return conv


@pytest.fixture
def mock_audit() -> AsyncMock:
    audit = AsyncMock()
    audit.log = AsyncMock()
    return audit


@pytest.fixture
def mock_settings() -> AsyncMock:
    s = AsyncMock()
    return s


@pytest.fixture
def chat_use_case(mock_llm, mock_memory, mock_conversations, mock_audit, mock_settings):
    return ChatUseCase(
        llm=mock_llm,
        memory=mock_memory,
        conversations=mock_conversations,
        audit=mock_audit,
        settings=mock_settings,
    )


@pytest.mark.asyncio
async def test_chat_returns_response(chat_use_case, mock_llm):
    result = await chat_use_case.chat("Oi!")
    assert isinstance(result, str)
    assert len(result) > 0
    mock_llm.complete.assert_called_once()


@pytest.mark.asyncio
async def test_chat_saves_conversation(chat_use_case, mock_conversations):
    await chat_use_case.chat("Oi!")
    mock_conversations.save.assert_called_once()


@pytest.mark.asyncio
async def test_chat_searches_memory(chat_use_case, mock_memory):
    await chat_use_case.chat("Oi!")
    mock_memory.search.assert_called_once()


@pytest.mark.asyncio
async def test_chat_saves_preference_memory(chat_use_case, mock_memory):
    """Quando usuário menciona preferência, deve salvar memória."""
    await chat_use_case.chat("Meu nome é Ana e eu gosto de animes")
    mock_memory.save.assert_called()


@pytest.mark.asyncio
async def test_chat_logs_audit(chat_use_case, mock_audit):
    await chat_use_case.chat("Teste")
    mock_audit.log.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_existing_conversation(chat_use_case, mock_conversations):
    existing = Conversation()
    existing.add_message(
        __import__("core.entities.models", fromlist=["MessageRole"]).MessageRole.USER,
        "mensagem anterior",
    )
    mock_conversations.get.return_value = existing

    result = await chat_use_case.chat("Nova mensagem", conversation_id=existing.id)
    assert isinstance(result, str)
