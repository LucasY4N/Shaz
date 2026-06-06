"""
providers/llm/groq_provider.py
Implementação do LLMPort usando Groq (velocidade máxima).
"""
from __future__ import annotations
from typing import AsyncIterator
from groq import AsyncGroq
from core.ports.interfaces import LLMPort
from infrastructure.logging.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class GroqProvider(LLMPort):
    """Provedor LLM usando Groq — ultra-rápido para respostas em tempo real."""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model
        logger.info(f"[Groq] initialized model={model}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        try:
            msgs: list[dict[str, str]] = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            msgs.extend(messages)

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=msgs,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"[Groq] complete error: {e}")
            raise

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        msgs: list[dict[str, str]] = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages)

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=msgs,  # type: ignore[arg-type]
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
