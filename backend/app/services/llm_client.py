from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings


class LLMError(Exception):
    """Raised when an LLM call fails after retries."""


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
        raise LLMError(str(last_error)) from last_error

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
            raise LLMError(str(exc)) from exc


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
        raise LLMError(str(last_error)) from last_error

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
            raise LLMError(str(exc)) from exc


def get_llm_client(premium: bool = False) -> LLMClient:
    """Return an LLM client configured for the given tier.

    Free tier uses Gemini 2.0 Flash via Google's OpenAI-compatible API
    (free, accessible worldwide including HK, 15 RPM / 1M tokens/day).
    Premium tier uses a commercial model (OpenAI or Anthropic).
    """
    if premium:
        if settings.llm_premium_provider == "anthropic":
            return AnthropicClient(
                api_key=settings.llm_premium_api_key,
                model=settings.llm_premium_model,
            )
        return OpenAIClient(
            api_key=settings.llm_premium_api_key,
            model=settings.llm_premium_model,
        )
    # Free tier — open-source model via OpenAI-compatible API
    return OpenAIClient(
        api_key=settings.llm_free_api_key,
        model=settings.llm_free_model,
        base_url=settings.llm_free_base_url,
    )
