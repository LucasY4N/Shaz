"""
core/use_cases/youtube_learning.py
Extrair transcrição, resumo, conceitos, flashcards e perguntas de vídeos.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from core.ports.interfaces import LLMPort, YouTubePort, MemoryPort
from core.entities.models import Memory, MemoryType
from infrastructure.logging.logger import logger


@dataclass
class VideoKnowledge:
    url: str
    title: str
    summary: str
    key_concepts: list[str] = field(default_factory=list)
    flashcards: list[dict[str, str]] = field(default_factory=list)  # [{q, a}]
    questions: list[str] = field(default_factory=list)
    transcript_excerpt: str = ""


class YouTubeLearningUseCase:
    """Extrai e persiste conhecimento de vídeos do YouTube."""

    def __init__(
        self,
        llm: LLMPort,
        youtube: YouTubePort,
        memory: MemoryPort,
    ) -> None:
        self._llm = llm
        self._youtube = youtube
        self._memory = memory

    async def learn_from_video(self, url: str) -> VideoKnowledge:
        """Pipeline completo: transcrição → análise → persistência."""
        logger.info(f"[YouTubeLearning] processing {url}")

        # 1. Extrair transcrição
        transcript = await self._youtube.get_transcript(url)
        if not transcript:
            raise ValueError(f"Não foi possível extrair transcrição de {url}")

        # 2. Resumo
        summary = await self._summarize(transcript)

        # 3. Conceitos-chave
        concepts = await self._extract_concepts(transcript)

        # 4. Flashcards
        flashcards = await self._generate_flashcards(transcript)

        # 5. Perguntas de reflexão
        questions = await self._generate_questions(transcript)

        knowledge = VideoKnowledge(
            url=url,
            title=url,  # YouTube provider pode enriquecer
            summary=summary,
            key_concepts=concepts,
            flashcards=flashcards,
            questions=questions,
            transcript_excerpt=transcript[:500],
        )

        # 6. Salvar apenas conhecimento relevante na memória
        await self._persist(knowledge)

        return knowledge

    async def _summarize(self, transcript: str) -> str:
        prompt = f"Resuma este conteúdo em até 5 frases concisas:\n\n{transcript[:3000]}"
        return await self._llm.complete([{"role": "user", "content": prompt}], temperature=0.3)

    async def _extract_concepts(self, transcript: str) -> list[str]:
        prompt = (
            f"Liste os 5 principais conceitos deste conteúdo como uma lista Python de strings:\n\n"
            f"{transcript[:3000]}\n\nResponda APENAS: [\"conceito1\", ...]"
        )
        raw = await self._llm.complete([{"role": "user", "content": prompt}], temperature=0.2)
        import ast, re
        try:
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            return ast.literal_eval(match.group()) if match else []
        except Exception:
            return []

    async def _generate_flashcards(self, transcript: str) -> list[dict[str, str]]:
        prompt = (
            "Crie 5 flashcards (pergunta/resposta) sobre este conteúdo.\n"
            f"Responda APENAS com JSON: [{{\"q\":\"...\",\"a\":\"...\"}}]\n\n{transcript[:2000]}"
        )
        raw = await self._llm.complete([{"role": "user", "content": prompt}], temperature=0.4)
        import json, re
        try:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            return json.loads(match.group()) if match else []
        except Exception:
            return []

    async def _generate_questions(self, transcript: str) -> list[str]:
        prompt = (
            "Gere 3 perguntas de reflexão profunda sobre este conteúdo.\n"
            "Responda como lista Python de strings.\n\n" + transcript[:2000]
        )
        raw = await self._llm.complete([{"role": "user", "content": prompt}], temperature=0.5)
        import ast, re
        try:
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            return ast.literal_eval(match.group()) if match else []
        except Exception:
            return []

    async def _persist(self, knowledge: VideoKnowledge) -> None:
        """Salva apenas conhecimento relevante (importance >= 0.6)."""
        mem = Memory(
            type=MemoryType.KNOWLEDGE,
            content=(
                f"[YouTube] {knowledge.url}\n"
                f"Resumo: {knowledge.summary}\n"
                f"Conceitos: {', '.join(knowledge.key_concepts)}"
            ),
            tags=["youtube", "aprendizado"],
            importance=0.8,
        )
        await self._memory.save(mem)
        logger.info(f"[YouTubeLearning] knowledge saved: {mem.id}")
