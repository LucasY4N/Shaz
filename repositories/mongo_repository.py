"""
repositories/mongo_repository.py
Implementação MongoDB de todos os repositórios (Memory, Conversation, Audit, Settings).
Usa motor para operações assíncronas.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import motor.motor_asyncio
from core.entities.models import (
    Memory, MemoryType, Conversation, AuditLog, UserPreferences,
)
from core.ports.interfaces import (
    MemoryPort, ConversationPort, AuditPort, UserSettingsPort,
)
from infrastructure.logging.logger import logger


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MongoClient:
    """Singleton do cliente MongoDB."""
    _instance: motor.motor_asyncio.AsyncIOMotorClient | None = None

    @classmethod
    def get(cls, uri: str) -> motor.motor_asyncio.AsyncIOMotorClient:
        if cls._instance is None:
            cls._instance = motor.motor_asyncio.AsyncIOMotorClient(uri)
            logger.info("[MongoDB] client connected")
        return cls._instance


class MongoMemoryRepository(MemoryPort):
    """Repositório de memórias no MongoDB com índices e TTL."""

    def __init__(self, db: Any) -> None:
        self._col = db["memory"]

    async def setup_indexes(self) -> None:
        """Cria índices necessários. Chamar na inicialização."""
        await self._col.create_index("type")
        await self._col.create_index("tags")
        await self._col.create_index("importance")
        # TTL: short_term expira em 24h
        await self._col.create_index(
            "expires_at",
            expireAfterSeconds=0,
            sparse=True,
        )
        logger.info("[MongoDB] memory indexes created")

    async def save(self, memory: Memory) -> str:
        doc = memory.model_dump()
        await self._col.update_one(
            {"id": memory.id},
            {"$set": doc},
            upsert=True,
        )
        return memory.id

    async def get(self, memory_id: str) -> Memory | None:
        doc = await self._col.find_one({"id": memory_id})
        return Memory(**doc) if doc else None

    async def search(
        self,
        query: str,
        type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        filter_: dict[str, Any] = {"content": {"$regex": query, "$options": "i"}}
        if type:
            filter_["type"] = type.value
        cursor = self._col.find(filter_).sort("importance", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Memory(**d) for d in docs]

    async def delete(self, memory_id: str) -> bool:
        result = await self._col.delete_one({"id": memory_id})
        return result.deleted_count > 0

    async def summarize_and_compress(self, conversation_id: str) -> str:
        """Placeholder — implementação real usa LLM para resumir memórias antigas."""
        return f"Resumo comprimido para conversa {conversation_id}"


class MongoConversationRepository(ConversationPort):
    """Repositório de conversas no MongoDB."""

    def __init__(self, db: Any) -> None:
        self._col = db["conversations"]

    async def setup_indexes(self) -> None:
        await self._col.create_index("id", unique=True)
        await self._col.create_index([("updated_at", -1)])

    async def save(self, conversation: Conversation) -> str:
        doc = conversation.model_dump()
        await self._col.update_one(
            {"id": conversation.id},
            {"$set": doc},
            upsert=True,
        )
        return conversation.id

    async def get(self, conversation_id: str) -> Conversation | None:
        doc = await self._col.find_one({"id": conversation_id})
        return Conversation(**doc) if doc else None

    async def list_recent(self, limit: int = 10) -> list[Conversation]:
        cursor = self._col.find().sort("updated_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [Conversation(**d) for d in docs]


class MongoAuditRepository(AuditPort):
    """Repositório de auditoria no MongoDB."""

    def __init__(self, db: Any) -> None:
        self._col = db["audit"]

    async def setup_indexes(self) -> None:
        await self._col.create_index("timestamp")
        await self._col.create_index("actor")

    async def log(self, entry: AuditLog) -> None:
        await self._col.insert_one(entry.model_dump())

    async def get_logs(
        self, actor: str | None = None, limit: int = 50
    ) -> list[AuditLog]:
        filter_: dict[str, Any] = {}
        if actor:
            filter_["actor"] = actor
        cursor = self._col.find(filter_).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [AuditLog(**d) for d in docs]


class MongoUserSettingsRepository(UserSettingsPort):
    """Repositório de preferências do usuário."""

    def __init__(self, db: Any) -> None:
        self._col = db["settings"]

    async def get(self, user_id: str) -> UserPreferences:
        doc = await self._col.find_one({"user_id": user_id})
        if doc:
            doc.pop("_id", None)
            return UserPreferences(**doc)
        return UserPreferences(user_id=user_id)

    async def save(self, prefs: UserPreferences) -> None:
        await self._col.update_one(
            {"user_id": prefs.user_id},
            {"$set": prefs.model_dump()},
            upsert=True,
        )
