"""
core/ports/interfaces.py
Portas (interfaces abstratas) da arquitetura hexagonal.
O core depende apenas destas abstrações — nunca de implementações concretas.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from core.entities.models import (
    Conversation, Memory, MemoryType, Message,
    UserPreferences, AuditLog, ImageStyle, VoiceEmotion,
)


# ─── LLM Port ────────────────────────────────────────────────────────────────

class LLMPort(ABC):
    """Interface para qualquer provedor de modelo de linguagem."""

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]: ...


# ─── Memory Port ─────────────────────────────────────────────────────────────

class MemoryPort(ABC):
    """Interface para persistência e recuperação de memórias."""

    @abstractmethod
    async def save(self, memory: Memory) -> str: ...

    @abstractmethod
    async def get(self, memory_id: str) -> Memory | None: ...

    @abstractmethod
    async def search(
        self,
        query: str,
        type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[Memory]: ...

    @abstractmethod
    async def delete(self, memory_id: str) -> bool: ...

    @abstractmethod
    async def summarize_and_compress(self, conversation_id: str) -> str: ...


# ─── Conversation Port ────────────────────────────────────────────────────────

class ConversationPort(ABC):
    """Interface para persistência de conversas."""

    @abstractmethod
    async def save(self, conversation: Conversation) -> str: ...

    @abstractmethod
    async def get(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def list_recent(self, limit: int = 10) -> list[Conversation]: ...


# ─── TTS Port ────────────────────────────────────────────────────────────────

class TTSPort(ABC):
    """Interface para síntese de voz (Text-to-Speech)."""

    @abstractmethod
    async def speak(
        self,
        text: str,
        emotion: VoiceEmotion = VoiceEmotion.NEUTRAL,
        profile: str = "default",
    ) -> None: ...

    @abstractmethod
    async def to_audio_bytes(self, text: str, emotion: VoiceEmotion) -> bytes: ...


# ─── STT Port ────────────────────────────────────────────────────────────────

class STTPort(ABC):
    """Interface para reconhecimento de voz (Speech-to-Text)."""

    @abstractmethod
    async def listen(self) -> str: ...

    @abstractmethod
    async def transcribe_file(self, audio_path: str) -> str: ...


# ─── Image Generation Port ───────────────────────────────────────────────────

class ImageGenerationPort(ABC):
    """Interface para geração de imagens com provedores intercambiáveis."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        style: ImageStyle = ImageStyle.ANIME,
        width: int = 512,
        height: int = 512,
    ) -> bytes: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


# ─── Knowledge / YouTube Port ────────────────────────────────────────────────

class YouTubePort(ABC):
    """Interface para extração de conhecimento do YouTube."""

    @abstractmethod
    async def get_transcript(self, url: str) -> str: ...

    @abstractmethod
    async def extract_knowledge(self, url: str) -> dict[str, Any]: ...


# ─── Audit Port ──────────────────────────────────────────────────────────────

class AuditPort(ABC):
    """Interface para auditoria de ações."""

    @abstractmethod
    async def log(self, entry: AuditLog) -> None: ...

    @abstractmethod
    async def get_logs(
        self, actor: str | None = None, limit: int = 50
    ) -> list[AuditLog]: ...


# ─── Settings Port ───────────────────────────────────────────────────────────

class UserSettingsPort(ABC):
    """Interface para preferências do usuário."""

    @abstractmethod
    async def get(self, user_id: str) -> UserPreferences: ...

    @abstractmethod
    async def save(self, prefs: UserPreferences) -> None: ...
