"""
agents/memory_agent.py
Agente de memória: extrai, consolida e recupera memórias importantes.
Responsabilidade única: tudo relacionado ao sistema de memória.
"""
from __future__ import annotations

import re

from logs.logger import get_module_logger

log = get_module_logger(__name__)

MEMORY_TRIGGERS = [
    "meu nome", "eu gosto", "eu prefiro", "minha cor", "eu odeio",
    "moro em", "eu trabalho", "meu aniversário", "nasci em",
    "eu estudo", "meu time", "minha série", "meu filme favorito",
    "tenho um", "minha família", "meu pet",
]


class MemoryAgent:
    """
    Agente que gerencia extração e recuperação de memórias.
    Detecta informações importantes nas conversas e as persiste.
    """

    def __init__(self, memory_store) -> None:  # type: ignore[annotation]
        self._memory = memory_store

    async def extract_and_save(
        self, user_message: str, assistant_response: str, user_id: str = "default"
    ) -> int:
        """
        Extrai memórias importantes da conversa e persiste.

        Returns:
            Número de memórias salvas
        """
        saved = 0

        # Preferências do usuário
        if self._has_preference(user_message):
            self._memory.save_memory(
                content=f"Usuário disse: {user_message[:200]}",
                memory_type="preference",
                user_id=user_id,
                importance=0.7,
            )
            saved += 1
            log.debug(f"MemoryAgent saved preference: {user_message[:60]!r}")

        # Interações normais (importância baixa)
        self._memory.save_memory(
            content=f"[Interação] User='{user_message[:80]}' → Shaz='{assistant_response[:80]}'",
            memory_type="interaction",
            user_id=user_id,
            importance=0.2,
        )
        saved += 1

        return saved

    def get_relevant_context(self, query: str, user_id: str = "default") -> str:
        """Retorna contexto de memórias relevantes para a consulta."""
        return self._memory.get_memory_context(query, user_id, limit=5)

    def _has_preference(self, text: str) -> bool:
        t = text.lower()
        return any(trigger in t for trigger in MEMORY_TRIGGERS)
