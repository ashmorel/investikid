from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Literal, Protocol

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm_usage import record_usage

logger = logging.getLogger(__name__)

_failure_hook: Callable[[str], Awaitable[None]] | None = None


def set_failure_hook(hook: Callable[[str], Awaitable[None]] | None) -> None:
    global _failure_hook
    _failure_hook = hook


def _fire_failure_hook(detail: str) -> None:
    if _failure_hook is None:
        return
    try:
        asyncio.create_task(_failure_hook(detail))
    except RuntimeError:
        pass  # no running loop


def _is_openai_reasoning_model(model: str) -> bool:
    """GPT-5 family and o-series reasoning models require max_completion_tokens
    and reject a non-default temperature."""
    m = model.lower()
    return m.startswith("gpt-5") or m.startswith(("o1", "o3", "o4"))


# Reasoning models (gpt-5 / o-series) spend tokens on INTERNAL reasoning that
# count against max_completion_tokens BEFORE any visible output. A budget sized
# only for the answer (e.g. 60–1200) is consumed entirely by reasoning, yielding
# an EMPTY completion. So for reasoning models we floor the completion budget at
# a value large enough to cover reasoning + a full answer (empirically ~6.5k of
# reasoning + answer for the largest surface). Unused tokens are not billed, and
# actual answer length stays governed by the prompt — this only prevents the
# starve-to-empty failure. Non-reasoning models keep the caller's max_tokens.
_REASONING_MIN_COMPLETION_TOKENS = 12000

# Reasoning effort for gpt-5/o-series. "minimal" ≈ 0 reasoning tokens → ~3-5x
# faster + cheaper than the default; output stays valid for our simple,
# brief-grounded, human-reviewed tasks. Critically, fast per-call latency keeps
# sequential per-level lesson generation under the request timeout.
_REASONING_EFFORT = "minimal"


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


def _is_provider_auth_error(exc: LLMError) -> bool:
    """True for 401/403 — a bad/misconfigured key on THIS provider.

    The chain should advance to the next provider rather than failing the whole
    request, because the error is specific to this provider's credentials, not
    to the request itself.
    """
    cause = exc.__cause__
    status = getattr(cause, "status_code", None) or getattr(cause, "status", None)
    if isinstance(status, int) and status in (401, 403):
        return True
    msg = str(exc).lower()
    return (
        "401" in msg
        or "403" in msg
        or "unauthorized" in msg
        or "invalid api key" in msg
        or "invalid_api_key" in msg
    )


def _is_provider_unavailable_error(exc: LLMError) -> bool:
    """True when THIS provider can't serve the request for billing/quota reasons
    (out of credits, quota exceeded, billing not active). Like an auth error, the
    request itself is fine — advance to the next provider rather than failing."""
    msg = str(exc).lower()
    return (
        "credit balance" in msg
        or "insufficient_quota" in msg
        or "insufficient quota" in msg
        or "exceeded your current quota" in msg
        or "billing" in msg
    )


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
    def __init__(
        self, api_key: str, model: str, base_url: str | None = None, provider: str = "openai"
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._provider = provider

    async def complete(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Literal["text", "json"] = "text",
    ) -> str:
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        kwargs: dict = {"model": self._model, "messages": all_messages}
        if _is_openai_reasoning_model(self._model):
            # Floor the budget so internal reasoning can't starve the answer to
            # empty (see _REASONING_MIN_COMPLETION_TOKENS). Answer length stays
            # governed by the prompt, not this ceiling.
            kwargs["max_completion_tokens"] = max(max_tokens, _REASONING_MIN_COMPLETION_TOKENS)
            # Minimal reasoning effort: this app's tasks (lessons, briefs, coach
            # replies) are simple + brief-grounded + human-reviewed, so deep
            # reasoning adds ~3-5x latency and reasoning-token cost for no quality
            # gain — and slow per-call latency was timing out batch generation.
            kwargs["reasoning_effort"] = _REASONING_EFFORT
            # temperature: only the default (1) is supported → omit entirely
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        attempts = 0
        last_error: Exception | None = None
        while attempts < 2:
            try:
                response = await self._client.chat.completions.create(**kwargs)
                usage = getattr(response, "usage", None)
                if usage is not None:
                    record_usage(
                        provider=self._provider,
                        model=self._model,
                        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                    )
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
        stream_kwargs: dict = {"model": self._model, "messages": all_messages, "stream": True}
        if _is_openai_reasoning_model(self._model):
            stream_kwargs["max_completion_tokens"] = max_tokens
            # temperature: only the default (1) is supported → omit entirely
        else:
            stream_kwargs["max_tokens"] = max_tokens
            stream_kwargs["temperature"] = temperature
        try:
            response = await self._client.chat.completions.create(**stream_kwargs)
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            raise LLMError(str(exc), retryable=_is_retryable(exc)) from exc


def _strip_json_fences(text: str) -> str:
    """Remove a ```json … ``` (or plain ``` … ```) markdown fence some models wrap
    JSON in, so json.loads downstream works. Returns the inner text trimmed."""
    s = text.strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


class AnthropicClient:
    def __init__(self, api_key: str, model: str, provider: str = "anthropic") -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._provider = provider

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
        # Some Anthropic models (extended-thinking / reasoning variants such as
        # the Opus authoring model) reject a `temperature` argument outright
        # ("temperature is deprecated for this model"). Send it, but drop it and
        # retry if the API complains, so any model works without hardcoding names.
        send_temperature = True
        while attempts < 2:
            try:
                kwargs: dict = dict(
                    model=self._model,
                    system=system_prompt,
                    messages=messages,
                    max_tokens=max_tokens,
                )
                if send_temperature:
                    kwargs["temperature"] = temperature
                response = await self._client.messages.create(**kwargs)
                usage = getattr(response, "usage", None)
                if usage is not None:
                    record_usage(
                        provider=self._provider,
                        model=self._model,
                        prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
                        completion_tokens=getattr(usage, "output_tokens", 0) or 0,
                    )
                text = response.content[0].text
                # Anthropic has no native JSON mode; callers ask for JSON in the
                # prompt. Strip a ```json … ``` fence so json.loads downstream works.
                if response_format == "json":
                    text = _strip_json_fences(text)
                return text
            except Exception as exc:
                last_error = exc
                # Retry without temperature (not counting the attempt) when the
                # model rejects it, rather than failing the whole generation.
                if send_temperature and "temperature" in str(exc).lower():
                    send_temperature = False
                    continue
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
                should_fallback = (
                    e.retryable
                    or _is_provider_auth_error(e)
                    or _is_provider_unavailable_error(e)
                )
                if not should_fallback or i == len(self.clients) - 1:
                    raise
                logger.warning("Provider %d failed (retryable/auth), trying next: %s", i, e)
                last_error = e
                _fire_failure_hook(str(e))
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
                should_fallback = (
                    e.retryable
                    or _is_provider_auth_error(e)
                    or _is_provider_unavailable_error(e)
                )
                if not should_fallback or i == len(self.clients) - 1:
                    raise
                logger.warning("Provider %d stream failed (retryable/auth), trying next: %s", i, e)
                last_error = e
                _fire_failure_hook(str(e))
        raise last_error  # type: ignore[misc]


def _build_together_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_together_api_key,
        model=settings.llm_together_model,
        base_url=settings.llm_together_base_url,
        provider="together",
    )


def _build_groq_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_groq_api_key,
        model=settings.llm_groq_model,
        base_url=settings.llm_groq_base_url,
        provider="groq",
    )


def _build_gemini_flash_lite_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_gemini_api_key,
        model=settings.llm_gemini_flash_lite_model,
        base_url=settings.llm_gemini_base_url,
        provider="gemini",
    )


def _build_gemini_flash_client() -> OpenAIClient:
    return OpenAIClient(
        api_key=settings.llm_gemini_api_key,
        model=settings.llm_gemini_flash_model,
        base_url=settings.llm_gemini_base_url,
        provider="gemini",
    )


_PROVIDER_BUILDERS: dict[str, tuple] = {
    "together": (_build_together_client, lambda: settings.llm_together_api_key),
    "groq": (_build_groq_client, lambda: settings.llm_groq_api_key),
    "gemini_flash_lite": (_build_gemini_flash_lite_client, lambda: settings.llm_gemini_api_key),
    "gemini_flash": (_build_gemini_flash_client, lambda: settings.llm_gemini_api_key),
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
    if tier == "authoring":
        return settings.llm_authoring_model or settings.llm_premium_model
    if tier == "premium":
        return settings.llm_premium_model
    if tier == "standard":
        return settings.llm_gemini_flash_model
    return settings.llm_gemini_flash_lite_model


def get_llm_client(tier: str = "lite", *, premium: bool | None = None) -> LLMClient:
    """Return an LLM client configured for the given tier.

    Tiers:
      - "lite"     — FallbackLLMClient over llm_lite_providers (default)
      - "standard" — FallbackLLMClient over llm_standard_providers
      - "premium"  — Single commercial client (OpenAI or Anthropic)
      - "authoring"— Best-quality model for offline content authoring; falls back
                     to premium when unconfigured.

    Backward compat: premium=True maps to tier="premium", premium=False to tier="lite".
    """
    if premium is not None:
        tier = "premium" if premium else "lite"
    if tier == "authoring":
        # Best-quality model for OFFLINE content authoring (curriculum designer +
        # lesson/brief generation). Falls back to the premium tier (which itself
        # falls back to standard) when unconfigured, so generation always has a
        # model and this ships inert until an authoring key+model are set.
        if settings.llm_authoring_api_key and settings.llm_authoring_model:
            if settings.llm_authoring_provider == "anthropic":
                authoring: LLMClient = AnthropicClient(
                    api_key=settings.llm_authoring_api_key,
                    model=settings.llm_authoring_model,
                    provider="anthropic-authoring",
                )
            else:
                authoring = OpenAIClient(
                    api_key=settings.llm_authoring_api_key,
                    model=settings.llm_authoring_model,
                    provider="openai-authoring",
                )
            return FallbackLLMClient(clients=[authoring, get_llm_client("premium")])
        return get_llm_client("premium")
    if tier == "premium":
        clients: list[LLMClient] = []
        if settings.llm_premium_api_key:
            if settings.llm_premium_provider == "anthropic":
                clients.append(AnthropicClient(
                    api_key=settings.llm_premium_api_key,
                    model=settings.llm_premium_model,
                    provider="anthropic-premium",
                ))
            else:
                clients.append(OpenAIClient(
                    api_key=settings.llm_premium_api_key,
                    model=settings.llm_premium_model,
                    provider="openai-premium",
                ))
        # Fall back to the standard (open-source) providers when the premium
        # provider is unconfigured or fails (quota/5xx are retryable), so
        # premium users never lose the AI helper over a billing hiccup.
        clients.extend(_build_chain(settings.llm_standard_providers).clients)
        return FallbackLLMClient(clients=clients)
    if tier == "standard":
        return _build_chain(settings.llm_standard_providers)
    return _build_chain(settings.llm_lite_providers)


def get_strict_premium_client() -> LLMClient | None:
    """The commercial premium model with NO open-source fallback. Returns None when
    no premium key is configured. Used for answer verification, where silently
    degrading to the weak tier would defeat the check (it would just re-confirm the
    weak tier's own mistakes)."""
    if not settings.llm_premium_api_key:
        return None
    if settings.llm_premium_provider == "anthropic":
        return AnthropicClient(
            api_key=settings.llm_premium_api_key,
            model=settings.llm_premium_model,
            provider="anthropic-premium",
        )
    return OpenAIClient(
        api_key=settings.llm_premium_api_key,
        model=settings.llm_premium_model,
        provider="openai-premium",
    )


async def probe_provider(name: str) -> dict:
    """Ping one provider with a tiny prompt; report ok/error. Never returns the key."""
    entry = _PROVIDER_BUILDERS.get(name)
    if entry is None:
        return {"provider": name, "configured": False, "ok": False, "detail": "unknown provider"}
    builder, key_getter = entry
    api_key = key_getter()
    if not api_key:
        return {"provider": name, "configured": False, "ok": False, "detail": "no api key set"}
    client = builder()
    try:
        await client.complete(
            system_prompt="ping",
            messages=[{"role": "user", "content": "Reply with: OK"}],
            max_tokens=5,
            temperature=0,
        )
        return {"provider": name, "configured": True, "ok": True, "detail": "responded"}
    except Exception as exc:  # noqa: BLE001
        raw = f"{type(exc).__name__}: {exc}"[:200]
        # Scrub the API key from the error message — providers can echo it back in 401 bodies.
        safe_detail = raw.replace(api_key, "[REDACTED]") if api_key else raw
        return {
            "provider": name,
            "configured": True,
            "ok": False,
            "detail": safe_detail,
        }


async def probe_all_providers() -> list[dict]:
    """Probe every provider used by the lite/standard tiers + the premium tier."""
    names = ["gemini_flash_lite", "gemini_flash", "together"]
    results = [await probe_provider(n) for n in names]
    # premium (separate path — uses get_strict_premium_client)
    premium = get_strict_premium_client()
    if premium is None:
        results.append(
            {"provider": "premium", "configured": False, "ok": False, "detail": "no premium key set"}
        )
    else:
        try:
            await premium.complete(
                system_prompt="ping",
                messages=[{"role": "user", "content": "Reply with: OK"}],
                max_tokens=5,
                temperature=0,
            )
            results.append(
                {
                    "provider": "premium",
                    "model": get_model_name("premium"),
                    "configured": True,
                    "ok": True,
                    "detail": "responded",
                }
            )
        except Exception as exc:  # noqa: BLE001
            raw = f"{type(exc).__name__}: {exc}"[:200]
            # Scrub premium key from any error echoed back by the provider.
            premium_key = settings.llm_premium_api_key
            safe_detail = raw.replace(premium_key, "[REDACTED]") if premium_key else raw
            results.append(
                {
                    "provider": "premium",
                    "model": get_model_name("premium"),
                    "configured": True,
                    "ok": False,
                    "detail": safe_detail,
                }
            )
    return results
