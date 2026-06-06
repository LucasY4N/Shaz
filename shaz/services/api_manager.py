"""
shaz/services/api_manager.py
Gerenciamento de chamadas API com retry, rate limiting e fallback entre provedores.
Suporta OpenAI, OpenRouter, Groq, Gemini e Ollama.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from shaz.core.config import Config
from shaz.utils.logger import logger


# ─── Rate Limiter ─────────────────────────────────────────────────────────

class RateLimiter:
    """
    Rate limiter simples baseado em token bucket.
    """

    def __init__(self, max_calls: int = 60, period: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self._calls: List[float] = []

    async def acquire(self) -> None:
        """Aguarda até que uma chamada possa ser feita."""
        now = time.time()
        self._calls = [t for t in self._calls if now - t < self.period]

        if len(self._calls) >= self.max_calls:
            wait_time = self._calls[0] + self.period - now
            if wait_time > 0:
                logger.api(f"Rate limit reached. Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._calls.append(time.time())


# ─── Response Models ──────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    """Resposta padronizada do LLM."""
    content: str
    model: str = ""
    provider: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    finish_reason: str = ""


@dataclass
class LLMConfig:
    """Configuração para chamada LLM."""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    stop: Optional[List[str]] = None


# ─── LLM Provider Interface ──────────────────────────────────────────────

class LLMProvider:
    """
    Classe base abstrata para provedores LLM.
    """

    def __init__(self, config: Config, provider_name: str) -> None:
        self.config = config
        self.provider_name = provider_name
        self.rate_limiter = RateLimiter()
        cfg = config.get_llm_config(provider_name)
        # Extrai apenas os campos conhecidos do LLMConfig
        known_fields = {"model", "temperature", "max_tokens", "top_p", "stop"}
        filtered = {k: v for k, v in cfg.items() if k in known_fields}
        self._llm_config = LLMConfig(**filtered)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Chamada completa não-streaming."""
        raise NotImplementedError

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Chamada streaming."""
        raise NotImplementedError
        yield  # pragma: no cover


# ─── OpenAI Provider ──────────────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """Provedor OpenAI (e OpenRouter compatível)."""

    def __init__(self, config: Config, provider_name: str = "openai") -> None:
        super().__init__(config, provider_name)
        self._api_key = (
            config.openai_api_key if provider_name == "openai"
            else config.openrouter_api_key
        )
        self._base_url = (
            "https://api.openai.com/v1"
            if provider_name == "openai"
            else "https://openrouter.ai/api/v1"
        )

        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
            logger.api(f"{provider_name.title()} provider initialized")
        except ImportError:
            logger.error("[API] openai package not installed")
            self._client = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if self._client is None:
            return LLMResponse(content="", provider=self.provider_name)

        await self.rate_limiter.acquire()
        start_time = time.time()

        try:
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            response = await self._client.chat.completions.create(
                model=self._llm_config.model,
                messages=full_messages,
                temperature=temperature or self._llm_config.temperature,
                max_tokens=max_tokens or self._llm_config.max_tokens,
                top_p=self._llm_config.top_p,
                stop=self._llm_config.stop,
            )

            latency = (time.time() - start_time) * 1000
            choice = response.choices[0]

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.provider_name,
                tokens_prompt=response.usage.prompt_tokens if response.usage else 0,
                tokens_completion=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                latency_ms=latency,
                finish_reason=choice.finish_reason or "",
            )

        except Exception as e:
            logger.error(f"[{self.provider_name}] API error: {e}")
            return LLMResponse(
                content=f"Desculpe, ocorreu um erro: {str(e)}",
                provider=self.provider_name,
            )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        if self._client is None:
            return

        try:
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            stream = await self._client.chat.completions.create(
                model=self._llm_config.model,
                messages=full_messages,
                temperature=temperature or self._llm_config.temperature,
                max_tokens=max_tokens or self._llm_config.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"[{self.provider_name}] Stream error: {e}")
            yield f"\n[Erro: {str(e)}]"


# ─── Groq Provider ────────────────────────────────────────────────────────

class GroqProvider(LLMProvider):
    """Provedor Groq (LPU Inference)."""

    def __init__(self, config: Config) -> None:
        super().__init__(config, "groq")
        self._api_key = config.groq_api_key

        try:
            from groq import AsyncGroq
            self._client = AsyncGroq(api_key=self._api_key)
            logger.api("Groq provider initialized")
        except ImportError:
            logger.error("[API] groq package not installed")
            self._client = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if self._client is None:
            return LLMResponse(content="", provider="groq")

        await self.rate_limiter.acquire()
        start_time = time.time()

        try:
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            response = await self._client.chat.completions.create(
                model=self._llm_config.model,
                messages=full_messages,
                temperature=temperature or self._llm_config.temperature,
                max_tokens=max_tokens or self._llm_config.max_tokens,
            )

            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                provider="groq",
                latency_ms=latency,
            )

        except Exception as e:
            logger.error(f"[Groq] API error: {e}")
            return LLMResponse(content=f"Erro: {str(e)}", provider="groq")


# ─── Gemini Provider ──────────────────────────────────────────────────────

class GeminiProvider(LLMProvider):
    """Provedor Google Gemini."""

    def __init__(self, config: Config) -> None:
        super().__init__(config, "gemini")
        self._api_key = config.gemini_api_key

        try:
            import google.genai as genai
            self._client = genai.Client(api_key=self._api_key)
            self._genai = genai
            logger.api("Gemini provider initialized")
        except ImportError:
            logger.error("[API] google-genai package not installed")
            self._client = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if self._client is None:
            return LLMResponse(content="", provider="gemini")

        await self.rate_limiter.acquire()
        start_time = time.time()

        try:
            from google.genai import types

            history = []
            for m in messages[:-1]:
                role = "model" if m["role"] == "assistant" else "user"
                history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part(text=m["content"])],
                    )
                )

            config_args = {
                "temperature": temperature or self._llm_config.temperature,
                "max_output_tokens": max_tokens or self._llm_config.max_tokens,
            }
            if system_prompt:
                config_args["system_instruction"] = system_prompt

            config = types.GenerateContentConfig(**config_args)

            chat = self._client.aio.chats.create(
                model=self._llm_config.model,
                history=history,
                config=config,
            )

            last_msg = messages[-1]["content"]
            response = await chat.send_message(last_msg)

            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                content=response.text,
                model=self._llm_config.model,
                provider="gemini",
                latency_ms=latency,
            )

        except Exception as e:
            logger.error(f"[Gemini] API error: {e}")
            return LLMResponse(content=f"Erro: {str(e)}", provider="gemini")


# ─── Ollama Provider ──────────────────────────────────────────────────────

class OllamaProvider(LLMProvider):
    """Provedor Ollama (local)."""

    def __init__(self, config: Config) -> None:
        super().__init__(config, "ollama")
        self._base_url = config.ollama_base_url

        try:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=60.0)
            self._httpx = httpx
            logger.api(f"Ollama provider initialized (url={self._base_url})")
        except ImportError:
            logger.error("[API] httpx not installed")
            self._http_client = None

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if self._http_client is None:
            return LLMResponse(content="", provider="ollama")

        await self.rate_limiter.acquire()
        start_time = time.time()

        try:
            full_messages = []
            if system_prompt:
                full_messages.append({"role": "system", "content": system_prompt})
            full_messages.extend(messages)

            response = await self._http_client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._llm_config.model,
                    "messages": full_messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature or self._llm_config.temperature,
                        "num_predict": max_tokens or self._llm_config.max_tokens,
                    },
                },
            )

            response.raise_for_status()
            data = response.json()

            latency = (time.time() - start_time) * 1000

            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                model=data.get("model", self._llm_config.model),
                provider="ollama",
                latency_ms=latency,
            )

        except Exception as e:
            logger.error(f"[Ollama] API error: {e}")
            return LLMResponse(content=f"Erro: {str(e)}", provider="ollama")


# ─── API Manager ──────────────────────────────────────────────────────────

class APIManager:
    """
    Gerenciador central de chamadas API com fallback automático entre provedores.
    Tenta o provedor primário e fallback para alternativos em caso de falha.
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or Config()
        self._providers: Dict[str, LLMProvider] = {}
        self._primary_provider: str = self._config.llm_provider
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Inicializa todos os provedores disponíveis."""
        providers_map = {
            "openai": ("openai", OpenAIProvider),
            "openrouter": ("openrouter", OpenAIProvider),
            "groq": ("groq", GroqProvider),
            "gemini": ("gemini", GeminiProvider),
            "ollama": ("ollama", OllamaProvider),
        }

        for name, (config_key, provider_class) in providers_map.items():
            try:
                if name == "openrouter":
                    if self._config.openrouter_api_key:
                        self._providers[name] = provider_class(self._config, "openrouter")
                elif name == "openai":
                    if self._config.openai_api_key:
                        self._providers[name] = provider_class(self._config, "openai")
                elif name == "groq":
                    if self._config.groq_api_key:
                        self._providers[name] = provider_class(self._config)
                elif name == "gemini":
                    if self._config.gemini_api_key:
                        self._providers[name] = provider_class(self._config)
                elif name == "ollama":
                    self._providers[name] = provider_class(self._config)
            except Exception as e:
                logger.warning(f"[API] Failed to initialize {name}: {e}")

        if self._providers:
            logger.api(f"API Manager initialized | providers: {list(self._providers.keys())}")
        else:
            logger.warning("[API] No providers available")

    async def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> LLMResponse:
        """
        Faz uma chamada completa com fallback automático.

        Args:
            messages: Lista de mensagens no formato {role, content}
            system_prompt: Prompt de sistema
            temperature: Temperatura (criatividade)
            max_tokens: Máximo de tokens na resposta
            provider: Provedor específico (usa o primário se None)

        Returns:
            LLMResponse com o conteúdo da resposta
        """
        target_provider = provider or self._primary_provider
        providers_to_try = [target_provider]

        # Adiciona fallbacks
        for prov in ["openai", "groq", "gemini", "ollama", "openrouter"]:
            if prov != target_provider and prov in self._providers:
                providers_to_try.append(prov)

        last_error = ""

        for prov_name in providers_to_try:
            provider_instance = self._providers.get(prov_name)
            if provider_instance is None:
                continue

            logger.api(f"Calling {prov_name}...")
            response = await provider_instance.complete(
                messages, system_prompt, temperature, max_tokens
            )

            if response.content and not response.content.startswith("Erro:"):
                return response

            last_error = response.content
            logger.api(f"{prov_name} failed, trying next...")

        return LLMResponse(
            content=f"Desculpe, não consegui processar sua solicitação. Todos os provedores falharam. Último erro: {last_error}",
            provider="none",
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Faz uma chamada streaming.

        Args:
            messages: Lista de mensagens
            system_prompt: Prompt de sistema
            temperature: Temperatura
            max_tokens: Máximo de tokens
            provider: Provedor específico

        Yields:
            Chunks de texto da resposta
        """
        target_provider = provider or self._primary_provider
        provider_instance = self._providers.get(target_provider)

        if provider_instance is None:
            yield "Provedor não disponível."
            return

        try:
            async for chunk in provider_instance.stream(
                messages, system_prompt, temperature, max_tokens
            ):
                yield chunk
        except Exception as e:
            logger.error(f"[API] Stream error: {e}")
            yield f"\n[Erro: {str(e)}]"

    def set_provider(self, provider: str) -> bool:
        """Define o provedor primário."""
        if provider in self._providers:
            self._primary_provider = provider
            self._config.llm_provider = provider
            logger.api(f"Primary provider set to: {provider}")
            return True
        return False

    @property
    def available_providers(self) -> List[str]:
        """Lista provedores disponíveis."""
        return list(self._providers.keys())

    @property
    def current_provider(self) -> str:
        return self._primary_provider