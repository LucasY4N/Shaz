"""
backend/schemas/responses.py
Schemas Pydantic para respostas da API.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class ChatResponse(BaseModel):
    response: str
    tokens: int = 0
    provider: str = ""


class StatusResponse(BaseModel):
    online: bool = True
    version: str
    voice_active: bool = False
    messages_session: int = 0
    tokens_session: int = 0
    current_provider: str = ""
    available_providers: list[str] = []
    services: dict[str, str] = {}


class MemoryEntry(BaseModel):
    content: str
    type: str
    importance: float = 0.5
    created_at: str = ""


class StatsResponse(BaseModel):
    messages: int = 0
    tokens: int = 0
    memories: int = 0
    current_provider: str = ""
    providers: list[str] = []
    voice_active: bool = False


class ActionResponse(BaseModel):
    status: str
    message: str = ""
    data: Any = None
