from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Literal, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM call fails after retries."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


def _is_retryable(exc: Exception | None) -> bool:
    if exc is None:
        return False
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    msg = str(exc).lower()
    return "rate" in msg or "timeout" in msg or "503" in msg or "502" in msg or "429" in msg


class LLMClient(Protocol):
    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str: ...

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]: ...


class OpenAIClient:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        kwargs: dict = {
            "model": self._model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        attempts = 0
        last_error: Exception | None = None
        while attempts < 2:
            try:
                response = await self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
                attempts += 1
        raise LLMError(str(last_error), retryable=_is_retryable(last_error)) from last_error

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=all_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            raise LLMError(str(exc), retryable=_is_retryable(exc)) from exc


class AnthropicClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        attempts = 0
        last_error: Exception | None = None
        while attempts < 2:
            try:
                response = await self._client.messages.create(
                    model=self._model,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.content[0].text
            except Exception as exc:
                last_error = exc
                attempts += 1
        raise LLMError(str(last_error), retryable=_is_retryable(last_error)) from last_error

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        try:
            async with self._client.messages.stream(
                model=self._model,
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            raise LLMError(str(exc), retryable=_is_retryable(exc)) from exc


class FallbackLLMClient:
    """Wraps multiple LLMClients, trying each in order on retryable failures."""

    def __init__(self, clients: list[LLMClient]) -> None:
        self.clients = clients

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        if not self.clients:
            raise LLMError("No LLM providers are configured", retryable=False)
        last_error: LLMError | None = None
        for i, client in enumerate(self.clients):
            try:
                return await client.complete(
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            except LLMError as e:
                if not e.retryable or i == len(self.clients) - 1:
                    raise
                logger.warning("Provider %d failed (retryable), trying next: %s", i, e)
                last_error = e
        raise last_error  # type: ignore[misc]  # unreachable if clients is non-empty

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        if not self.clients:
            raise LLMError("No LLM providers are configured", retryable=False)
        last_error: LLMError | None = None
        for i, client in enumerate(self.clients):
            try:
                async for chunk in await client.stream(
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                return
            except LLMError as e:
                if not e.retryable or i == len(self.clients) - 1:
                    raise
                logger.warning("Provider %d stream failed (retryable), trying next: %s", i, e)
                last_error = e
        raise last_error  # type: ignore[misc]


def _build_together_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_together_api_key,
        model=settings.llm_together_model,
        base_url=settings.llm_together_base_url,
    )


def _build_groq_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_groq_api_key,
        model=settings.llm_groq_model,
        base_url=settings.llm_groq_base_url,
    )


_PROVIDER_BUILDERS: dict[str, tuple] = {
    "together": (_build_together_client, lambda: settings.llm_together_api_key),
    "groq": (_build_groq_client, lambda: settings.llm_groq_api_key),
}


def _build_chain(provider_csv: str) -> FallbackLLMClient:
    clients: list[LLMClient] = []
    for name in (p.strip() for p in provider_csv.split(",") if p.strip()):
        entry = _PROVIDER_BUILDERS.get(name)
        if entry is None:
            logger.warning("Unknown LLM provider %r, skipping", name)
            continue
        builder, key_getter = entry
        if not key_getter():
            logger.debug("Skipping provider %r — API key is empty", name)
            continue
        clients.append(builder())
    return FallbackLLMClient(clients=clients)


def get_model_name(tier: str = "lite") -> str:
    if tier == "premium":
        return settings.llm_premium_model
    return settings.llm_together_model


def get_llm_client(tier: str = "lite", *, premium: bool | None = None) -> LLMClient:
    """Return an LLM client configured for the given tier.

    Tiers:
      - "lite"     — FallbackLLMClient over llm_lite_providers (default)
      - "standard" — FallbackLLMClient over llm_standard_providers
      - "premium"  — Single commercial client (OpenAI or Anthropic)

    Backward compat: premium=True maps to tier="premium", premium=False to tier="lite".
    """
    if premium is not None:
        tier = "premium" if premium else "lite"
    if tier == "premium":
        if settings.llm_premium_provider == "anthropic":
            return AnthropicClient(
                api_key=settings.llm_premium_api_key,
                model=settings.llm_premium_model,
            )
        return OpenAIClient(
            api_key=settings.llm_premium_api_key,
            model=settings.llm_premium_model,
        )
    if tier == "standard":
        return _build_chain(settings.llm_standard_providers)
    return _build_chain(settings.llm_lite_providers)
