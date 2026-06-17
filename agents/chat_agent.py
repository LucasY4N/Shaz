"""
agents/chat_agent.py
Agente de chat: gerencia a conversa principal com a Shaz.
Responsabilidade única: orquestrar uma troca de mensagem completa.
"""
from __future__ import annotations

from logs.logger import get_module_logger

log = get_module_logger(__name__)


class ChatAgent:
    """
    Agente responsável pela conversa principal.
    Coordena: histórico → sistema → LLM → memória → resposta.
    """

    def __init__(self, brain) -> None:  # type: ignore[annotation]
        self._brain = brain

    async def respond(self, message: str, user_id: str = "default") -> str:
        """
        Processa uma mensagem e retorna a resposta da Shaz.

        Args:
            message: Mensagem do usuário
            user_id: Identificador do usuário

        Returns:
            Resposta gerada pela IA
        """
        log.info(f"ChatAgent processing: {message[:60]!r}")
        return await self._brain.process_message(message)
