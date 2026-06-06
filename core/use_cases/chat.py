"""
core/use_cases/chat.py
Caso de uso principal: conversar com a IA.
"""
from __future__ import annotations
from core.entities.models import Conversation, Memory, MemoryType, MessageRole
from core.ports.interfaces import (
    LLMPort, MemoryPort, ConversationPort, AuditPort, UserSettingsPort,
)
from core.entities.models import AuditLog
from infrastructure.logging.logger import logger


SYSTEM_PROMPT = """Você é Shaz, uma assistente de IA inteligente, empática e altamente capaz.
Você possui memória de longo prazo, pode gerar imagens, ouvir e falar.
Responda sempre em português do Brasil, seja precisa e útil.
"""


class ChatUseCase:
    """Orquestra uma conversa completa com memória e auditoria."""

    def __init__(
        self,
        llm: LLMPort,
        memory: MemoryPort,
        conversations: ConversationPort,
        audit: AuditPort,
        settings: UserSettingsPort,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._conversations = conversations
        self._audit = audit
        self._settings = settings

    async def chat(
        self,
        user_message: str,
        conversation_id: str | None = None,
        user_id: str = "default",
    ) -> str:
        """Processa mensagem do usuário e retorna resposta da IA."""
        logger.info(f"[ChatUseCase] user={user_id} | msg={user_message[:60]}...")

        # 1. Carregar ou criar conversa
        conversation: Conversation
        if conversation_id:
            conv = await self._conversations.get(conversation_id)
            conversation = conv or Conversation()
        else:
            conversation = Conversation()

        # 2. Buscar memórias relevantes
        memories = await self._memory.search(user_message, limit=5)
        memory_context = self._format_memories(memories)

        # 3. Montar histórico de mensagens
        conversation.add_message(MessageRole.USER, user_message)
        history = [
            {"role": m.role.value, "content": m.content}
            for m in conversation.short_term_window
        ]

        system = SYSTEM_PROMPT
        if memory_context:
            system += f"\n\n## Memórias relevantes:\n{memory_context}"

        # 4. Chamar LLM
        response = await self._llm.complete(history, system_prompt=system)

        # 5. Salvar resposta
        conversation.add_message(MessageRole.ASSISTANT, response)
        await self._conversations.save(conversation)

        # 6. Extrair e salvar memória importante
        await self._maybe_save_memory(user_message, response)

        # 7. Auditar
        await self._audit.log(AuditLog(
            action="chat",
            actor=user_id,
            resource=conversation.id,
            details={"tokens_approx": len(response.split())},
        ))

        return response

    def _format_memories(self, memories: list[Memory]) -> str:
        if not memories:
            return ""
        lines = [f"- [{m.type.value}] {m.content}" for m in memories]
        return "\n".join(lines)

    async def _maybe_save_memory(self, user_msg: str, response: str) -> None:
        """Heurística simples: salva se o usuário compartilhou fato sobre si."""
        triggers = ["meu nome", "eu gosto", "eu prefiro", "minha cor", "eu odeio", "moro em"]
        if any(t in user_msg.lower() for t in triggers):
            mem = Memory(
                type=MemoryType.PREFERENCE,
                content=f"Usuário disse: {user_msg}",
                importance=0.7,
            )
            await self._memory.save(mem)
            logger.debug(f"[ChatUseCase] memória salva: {mem.content[:60]}")
