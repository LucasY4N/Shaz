"""
integrations/youtube/youtube_provider.py
Extração de transcrição e metadados do YouTube.
"""
from __future__ import annotations
from typing import Any
from youtube_transcript_api import YouTubeTranscriptApi
from core.ports.interfaces import YouTubePort
from infrastructure.logging.logger import logger
import re


def _extract_video_id(url: str) -> str:
    """Extrai o ID do vídeo de qualquer formato de URL do YouTube."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Não foi possível extrair ID do vídeo: {url}")


class YouTubeProvider(YouTubePort):
    """Integração com YouTube para extração de conhecimento."""

    PREFERRED_LANGS = ["pt", "pt-BR", "en"]

    async def get_transcript(self, url: str) -> str:
        """Retorna transcrição completa do vídeo como texto."""
        video_id = _extract_video_id(url)
        logger.info(f"[YouTube] fetching transcript for {video_id}")

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Tenta idiomas preferenciais
            transcript = None
            for lang in self.PREFERRED_LANGS:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            # Fallback: qualquer disponível
            if transcript is None:
                transcript = transcript_list.find_generated_transcript(
                    [t.language_code for t in transcript_list]
                )

            entries = transcript.fetch()
            text = " ".join(e["text"] for e in entries)
            logger.info(f"[YouTube] transcript length={len(text)} chars")
            return text

        except Exception as e:
            logger.error(f"[YouTube] transcript error: {e}")
            return ""

    async def extract_knowledge(self, url: str) -> dict[str, Any]:
        """Extrai metadados e transcrição em dict estruturado."""
        video_id = _extract_video_id(url)
        transcript = await self.get_transcript(url)

        return {
            "video_id": video_id,
            "url": url,
            "transcript": transcript,
            "transcript_length": len(transcript),
        }
