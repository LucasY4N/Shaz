"""
services/container.py
Container de injeção de dependências — monta todas as camadas do Shaz AI.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from infrastructure.config.settings import get_settings
from infrastructure.logging.logger import logger, setup_logger
from infrastructure.security.security import validate_env_secrets


@dataclass
class Container:
    """
    Contém todas as instâncias do sistema.
    Monte via Container.build() na inicialização da aplicação.
    """
    # Ports (interfaces) — preenchidos no build
    llm: object = field(default=None)
    memory: object = field(default=None)
    conversations: object = field(default=None)
    audit: object = field(default=None)
    user_settings: object = field(default=None)
    tts: object = field(default=None)
    stt: object = field(default=None)
    image_gen: object = field(default=None)
    youtube: object = field(default=None)

    # Use Cases
    chat_use_case: object = field(default=None)
    programming_use_case: object = field(default=None)
    youtube_use_case: object = field(default=None)

    @classmethod
    async def build(cls) -> "Container":
        """Monta o container completo com todas as dependências."""
        settings = get_settings()
        setup_logger(settings.log_level)

        # Validação de segurança
        missing = validate_env_secrets()
        if missing and settings.is_production:
            raise RuntimeError(f"Variáveis de ambiente faltando: {missing}")

        c = cls()

        # ── MongoDB ──────────────────────────────────────────────────────────
        from repositories.mongo_repository import (
            MongoClient,
            MongoMemoryRepository,
            MongoConversationRepository,
            MongoAuditRepository,
            MongoUserSettingsRepository,
        )
        mongo_client = MongoClient.get(settings.mongodb_uri)
        db = mongo_client[settings.mongodb_db]

        c.memory = MongoMemoryRepository(db)
        c.conversations = MongoConversationRepository(db)
        c.audit = MongoAuditRepository(db)
        c.user_settings = MongoUserSettingsRepository(db)

        # Setup indexes
        for repo in [c.memory, c.conversations, c.audit]:
            if hasattr(repo, "setup_indexes"):
                await repo.setup_indexes()  # type: ignore

        # ── LLM ──────────────────────────────────────────────────────────────
        if settings.gemini_api_key:
            from providers.llm.gemini_provider import GeminiProvider
            c.llm = GeminiProvider(settings.gemini_api_key, model=settings.gemini_model)
        elif settings.groq_api_key:
            from providers.llm.groq_provider import GroqProvider
            c.llm = GroqProvider(settings.groq_api_key)
        else:
            raise RuntimeError("Nenhum provedor LLM configurado (GEMINI_API_KEY ou GROQ_API_KEY)")

        # ── Voice ────────────────────────────────────────────────────────────
        from providers.voice.voice_providers import GoogleSTTProvider, Pyttsx3TTSProvider
        c.stt = GoogleSTTProvider()
        c.tts = Pyttsx3TTSProvider()

        # ── Image Generation ─────────────────────────────────────────────────
        from providers.image.image_providers import create_image_provider
        c.image_gen = create_image_provider(
            settings.image_provider,
            settings.replicate_api_key,
        )

        # ── YouTube ──────────────────────────────────────────────────────────
        from integrations.youtube.youtube_provider import YouTubeProvider
        c.youtube = YouTubeProvider()

        # ── Use Cases ────────────────────────────────────────────────────────
        from core.use_cases.chat import ChatUseCase
        from core.use_cases.programming_assistant import ProgrammingAssistantUseCase
        from core.use_cases.youtube_learning import YouTubeLearningUseCase

        c.chat_use_case = ChatUseCase(
            llm=c.llm,  # type: ignore
            memory=c.memory,  # type: ignore
            conversations=c.conversations,  # type: ignore
            audit=c.audit,  # type: ignore
            settings=c.user_settings,  # type: ignore
        )
        c.programming_use_case = ProgrammingAssistantUseCase(llm=c.llm)  # type: ignore
        c.youtube_use_case = YouTubeLearningUseCase(
            llm=c.llm,  # type: ignore
            youtube=c.youtube,  # type: ignore
            memory=c.memory,  # type: ignore
        )

        logger.info("[Container] ✅ Shaz AI initialized successfully")
        return c
