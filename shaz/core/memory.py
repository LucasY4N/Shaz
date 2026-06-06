"""
shaz/core/memory.py
Sistema de memória persistente usando SQLite.
Tabelas: users, messages, memory, settings, personality.
Carrega automaticamente o histórico e fatos aprendidos.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shaz.utils.logger import logger


class Memory:
    """
    Gerenciador de memória persistente via SQLite.
    Thread-safe com cache em memória para acesso rápido.
    """

    def __init__(self, db_path: str = "data/memory.db") -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
        self._cache: Dict[str, Any] = {}
        self._load_cache()
        logger.memory(f"Memory initialized | db={self._db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Obtém conexão thread-safe."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        """Cria as tabelas do banco de dados se não existirem."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tabela de usuários
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT DEFAULT '{}'
            )
        """)

        # Tabela de mensagens (histórico de conversas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                content TEXT NOT NULL,
                conversation_id TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Tabela de memórias (fatos aprendidos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN (
                    'fact', 'preference', 'knowledge', 'interaction', 'summary'
                )),
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Tabela de configurações
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de personalidade (lore + traços)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personality (
                id TEXT PRIMARY KEY,
                trait TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_user 
            ON messages(user_id, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON messages(conversation_id, timestamp ASC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_user 
            ON memory(user_id, importance DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memory(user_id, type, last_accessed DESC)
        """)

        conn.commit()

    def _load_cache(self) -> None:
        """Carrega dados frequentes em cache."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Carrega todas as configurações
        cursor.execute("SELECT key, value FROM settings")
        for row in cursor.fetchall():
            self._cache[f"settings:{row['key']}"] = row['value']

        # Carrega todos os traços de personalidade
        cursor.execute("SELECT trait, value, category FROM personality")
        for row in cursor.fetchall():
            self._cache[f"personality:{row['trait']}"] = {
                'value': row['value'],
                'category': row['category'],
            }

    # ─── User Management ────────────────────────────────────────────────

    def get_or_create_user(self, user_id: str = "default", name: str = "Usuário") -> Dict[str, Any]:
        """Obtém ou cria um usuário."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row is None:
            cursor.execute(
                "INSERT INTO users (id, name) VALUES (?, ?)",
                (user_id, name),
            )
            conn.commit()
            logger.memory(f"New user created: {user_id}")
            return {"id": user_id, "name": name, "preferences": {}}
        
        prefs = json.loads(row["preferences"]) if row["preferences"] else {}
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "last_seen": row["last_seen"],
            "preferences": prefs,
        }

    def update_user_seen(self, user_id: str = "default") -> None:
        """Atualiza o timestamp de último acesso do usuário."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,),
        )
        conn.commit()

    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        """Salva preferências do usuário."""
        conn = self._get_connection()
        conn.execute(
            "UPDATE users SET preferences = ? WHERE id = ?",
            (json.dumps(preferences, ensure_ascii=False), user_id),
        )
        conn.commit()
        logger.memory(f"Preferences saved for user {user_id}")

    # ─── Messages (Conversations) ───────────────────────────────────────

    def save_message(
        self,
        role: str,
        content: str,
        user_id: str = "default",
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Salva uma mensagem no histórico.

        Returns:
            Tuple (message_id, conversation_id)
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())

        message_id = str(uuid.uuid4())
        conn = self._get_connection()
        conn.execute(
            """INSERT INTO messages (id, user_id, role, content, conversation_id, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                message_id,
                user_id,
                role,
                content,
                conversation_id,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        conn.commit()
        return message_id, conversation_id

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 100,
        user_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """Obtém o histórico de uma conversa."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT role, content, timestamp, metadata
               FROM messages
               WHERE conversation_id = ? AND user_id = ?
               ORDER BY timestamp ASC
               LIMIT ?""",
            (conversation_id, user_id, limit),
        )

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
            }
            for row in cursor.fetchall()
        ]

    def get_recent_conversations(
        self,
        user_id: str = "default",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Obtém conversas recentes."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT conversation_id, COUNT(*) as msg_count,
                      MIN(timestamp) as first_msg, MAX(timestamp) as last_msg
               FROM messages
               WHERE user_id = ?
               GROUP BY conversation_id
               ORDER BY last_msg DESC
               LIMIT ?""",
            (user_id, limit),
        )

        return [
            {
                "id": row["conversation_id"],
                "message_count": row["msg_count"],
                "first_message": row["first_msg"],
                "last_message": row["last_msg"],
            }
            for row in cursor.fetchall()
        ]

    def get_recent_messages(
        self,
        user_id: str = "default",
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Obtém as mensagens mais recentes."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT role, content, timestamp, conversation_id
               FROM messages
               WHERE user_id = ?
               ORDER BY timestamp DESC
               LIMIT ?""",
            (user_id, limit),
        )

        return [
            {
                "role": row["role"],
                "content": row["content"],
                "timestamp": row["timestamp"],
            }
            for row in reversed(list(cursor.fetchall()))
        ]

    # ─── Memory (Facts) ─────────────────────────────────────────────────

    def save_memory(
        self,
        content: str,
        memory_type: str = "fact",
        user_id: str = "default",
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        expires_at: Optional[str] = None,
    ) -> str:
        """
        Salva um fato/memória sobre o usuário.

        Args:
            content: Conteúdo da memória
            memory_type: fact, preference, knowledge, interaction, summary
            user_id: ID do usuário
            tags: Lista de tags para categorização
            importance: Importância (0.0 a 1.0)
            expires_at: Data de expiração (opcional)

        Returns:
            ID da memória criada
        """
        memory_id = str(uuid.uuid4())
        conn = self._get_connection()

        conn.execute(
            """INSERT INTO memory (id, user_id, type, content, tags, importance, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                memory_id,
                user_id,
                memory_type,
                content,
                json.dumps(tags or [], ensure_ascii=False),
                importance,
                expires_at,
            ),
        )
        conn.commit()
        logger.memory(f"Memory saved [{memory_type}]: {content[:60]}...")
        return memory_id

    def search_memories(
        self,
        query: str,
        user_id: str = "default",
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Busca memórias relevantes baseado em texto (LIKE search).

        Args:
            query: Texto de busca
            user_id: ID do usuário
            memory_type: Filtrar por tipo (opcional)
            limit: Número máximo de resultados

        Returns:
            Lista de memórias encontradas
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        conditions = ["user_id = ?"]
        params: List[Any] = [user_id]

        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type)

        # Busca por palavras-chave na query
        keywords = query.lower().split()
        keyword_conditions = []
        for word in keywords:
            keyword_conditions.append("LOWER(content) LIKE ?")
            params.append(f"%{word}%")

        if keyword_conditions:
            conditions.append(f"({' OR '.join(keyword_conditions)})")

        where_clause = " AND ".join(conditions)

        cursor.execute(
            f"""SELECT id, type, content, tags, importance, created_at, access_count
                FROM memory
                WHERE {where_clause}
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY importance DESC, access_count DESC
                LIMIT ?""",
            params + [limit],
        )

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "type": row["type"],
                "content": row["content"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "importance": row["importance"],
                "created_at": row["created_at"],
            })
            # Atualiza contagem de acesso
            conn.execute(
                "UPDATE memory SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],),
            )

        conn.commit()
        return results

    def get_all_memories(
        self,
        user_id: str = "default",
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Obtém todas as memórias de um usuário."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if memory_type:
            cursor.execute(
                """SELECT id, type, content, tags, importance, created_at
                   FROM memory WHERE user_id = ? AND type = ?
                   ORDER BY importance DESC, created_at DESC LIMIT ?""",
                (user_id, memory_type, limit),
            )
        else:
            cursor.execute(
                """SELECT id, type, content, tags, importance, created_at
                   FROM memory WHERE user_id = ?
                   ORDER BY importance DESC, created_at DESC LIMIT ?""",
                (user_id, limit),
            )

        return [
            {
                "id": row["id"],
                "type": row["type"],
                "content": row["content"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "importance": row["importance"],
                "created_at": row["created_at"],
            }
            for row in cursor.fetchall()
        ]

    def delete_memory(self, memory_id: str) -> bool:
        """Deleta uma memória pelo ID."""
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ─── Settings ───────────────────────────────────────────────────────

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Obtém uma configuração."""
        # Tenta cache primeiro
        cache_key = f"settings:{key}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        conn = self._get_connection()
        cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()

        if row:
            value = row["value"]
            self._cache[cache_key] = value
            return value
        return default

    def set_setting(self, key: str, value: str) -> None:
        """Define uma configuração."""
        conn = self._get_connection()
        conn.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP""",
            (key, str(value)),
        )
        conn.commit()
        self._cache[f"settings:{key}"] = value

    def get_all_settings(self) -> Dict[str, str]:
        """Obtém todas as configurações."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    # ─── Personality ────────────────────────────────────────────────────

    def save_personality_trait(self, trait: str, value: str, category: str = "general") -> None:
        """Salva um traço de personalidade."""
        conn = self._get_connection()
        conn.execute(
            """INSERT INTO personality (id, trait, value, category, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(trait) DO UPDATE SET 
                   value = excluded.value, 
                   category = excluded.category,
                   updated_at = CURRENT_TIMESTAMP""",
            (str(uuid.uuid4()), trait, value, category),
        )
        conn.commit()
        self._cache[f"personality:{trait}"] = {"value": value, "category": category}

    def get_personality_trait(self, trait: str) -> Optional[str]:
        """Obtém um traço de personalidade."""
        cache_key = f"personality:{trait}"
        if cache_key in self._cache:
            return self._cache[cache_key]["value"]

        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT value FROM personality WHERE trait = ?", (trait,)
        )
        row = cursor.fetchone()
        if row:
            self._cache[cache_key] = {"value": row["value"]}
            return row["value"]
        return None

    def get_all_personality(self) -> Dict[str, Dict[str, str]]:
        """Obtém todos os traços de personalidade."""
        conn = self._get_connection()
        cursor = conn.execute("SELECT trait, value, category FROM personality")
        return {
            row["trait"]: {"value": row["value"], "category": row["category"]}
            for row in cursor.fetchall()
        }

    # ─── Utility ─────────────────────────────────────────────────────────

    def get_conversation_context(
        self,
        user_id: str = "default",
        max_messages: int = 20,
    ) -> List[Dict[str, str]]:
        """
        Obtém o contexto completo para enviar ao LLM:
        - Mensagens recentes formatadas
        """
        messages = self.get_recent_messages(user_id, limit=max_messages)
        return [
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ]

    def get_memory_context(
        self,
        query: str,
        user_id: str = "default",
        limit: int = 5,
    ) -> str:
        """
        Obtém memórias relevantes formatadas para contexto do LLM.
        """
        memories = self.search_memories(query, user_id, limit=limit)
        if not memories:
            return ""

        lines = ["## Memórias relevantes:"]
        for m in memories:
            lines.append(f"- [{m['type']}] {m['content']}")
        return "\n".join(lines)

    def clear_conversation_history(self, user_id: str = "default") -> int:
        """Limpa todo o histórico de conversas de um usuário."""
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM messages WHERE user_id = ?", (user_id,)
        )
        conn.commit()
        return cursor.rowcount

    def stats(self) -> Dict[str, int]:
        """Obtém estatísticas do banco de dados."""
        conn = self._get_connection()
        cursor = conn.cursor()

        stats = {}
        for table in ["users", "messages", "memory", "settings", "personality"]:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            row = cursor.fetchone()
            stats[table] = row["count"] if row else 0

        return stats

    def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None