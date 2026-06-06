"""
providers/llm/gemini_provider.py
Implementação do LLMPort usando Google Gemini (google.genai SDK).
"""
from __future__ import annotations
from typing import AsyncIterator
import google.genai as genai
from google.genai import types
from core.ports.interfaces import LLMPort
from infrastructure.logging.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class GeminiProvider(LLMPort):
    """Provedor LLM usando Google Gemini API (google.genai)."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model_name = model
        logger.info(f"[Gemini] initialized model={model}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def complete(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        try:
            # Gemini usa 'model' em vez de 'assistant'
            history: list[types.Content] = []
            for m in messages[:-1]:
                role = "model" if m["role"] == "assistant" else "user"
                history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=m["content"])],
                    )
                )

            config_args: dict = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if system_prompt:
                config_args["system_instruction"] = system_prompt

            config = types.GenerateContentConfig(**config_args)

            chat = self._client.aio.chats.create(
                model=self._model_name,
                history=history,
                config=config,
            )

            last = messages[-1]["content"]
            response = await chat.send_message(last)
            return response.text
        except Exception as e:
            logger.error(f"[Gemini] complete error: {e}")
            raise

    async def stream(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        contents = messages[-1]["content"]
        if system_prompt:
            contents = f"{system_prompt}\n\n{contents}"

        stream = await self._client.aio.models.generate_content_stream(
            model=self._model_name,
            contents=contents,
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text