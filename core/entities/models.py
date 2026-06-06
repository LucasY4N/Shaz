"""
core/entities/models.py
Entidades de domínio puras — sem dependências externas.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


# ─── Enums ──────────────────────────────────────────────────────────────────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    KNOWLEDGE = "knowledge"
    PREFERENCE = "preference"
    SUMMARY = "summary"


class VoiceEmotion(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    CALM = "calm"


class ImageStyle(str, Enum):
    ANIME = "anime"
    MANGA = "manga"
    WALLPAPER = "wallpaper"
    FANTASY = "fantasy"
    REALISTIC = "realistic"


# ─── Core Models ─────────────────────────────────────────────────────────────

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str | None = None

    def add_message(self, role: MessageRole, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg

    @property
    def short_term_window(self, n: int = 20) -> list[Message]:
        """Últimas N mensagens para contexto imediato."""
        return self.messages[-n:]


class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class UserPreferences(BaseModel):
    user_id: str
    voice_profile: str = "default"
    preferred_emotion: VoiceEmotion = VoiceEmotion.NEUTRAL
    preferred_image_style: ImageStyle = ImageStyle.ANIME
    language: str = "pt-BR"
    settings: dict[str, Any] = Field(default_factory=dict)


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    actor: str
    resource: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
