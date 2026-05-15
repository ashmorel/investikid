# Hybrid LLM Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-tier LLM setup (free Gemini / premium GPT-4o) with a three-tier architecture (lite/standard/premium) using Together AI and Groq for open-source tiers, with automatic provider fallback.

**Architecture:** New `FallbackLLMClient` wraps a chain of OpenAI-compatible providers, tried in order. `get_llm_client()` gains a `tier` parameter replacing the `premium` boolean. All 7 call sites migrate from `premium=True/False` to `tier="lite"/"standard"/"premium"`. Config gains Together AI + Groq fields, old Gemini free-tier fields are removed.

**Tech Stack:** Python 3.12, AsyncOpenAI (openai SDK), pydantic-settings, pytest, pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `app/core/config.py` | Modify | Add Together/Groq settings, remove old free-tier settings |
| `app/services/llm_client.py` | Modify | Add `FallbackLLMClient`, `get_model_name()`, refactor `get_llm_client()` to tier-based routing |
| `app/routers/simulator.py` | Modify | Change 4 call sites from `premium=False` to `tier="lite"` or `tier="standard"` |
| `app/services/chart_coach_service.py` | Modify | Change call site + `model_name` to tier-based |
| `app/services/tutor_service.py` | Modify | Change call site + `model_name` to tier-based |
| `app/services/ai_content_service.py` | Modify | Change call site to tier-based |
| `tests/test_llm_client.py` | Modify | Replace old tests, add FallbackLLMClient tests + tier routing tests |
| `backend/.env.example` | Modify | Add new env vars, remove old ones |

---

### Task 1: Configuration — Add Together AI and Groq Settings

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Update config.py with new settings**

Replace the free-tier LLM block and add Together/Groq config in `app/core/config.py`. Change lines 20-23 from:

```python
    # LLM / AI — free tier (Gemini Flash via Google's OpenAI-compatible API)
    llm_free_api_key: str = ""
    llm_free_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_free_model: str = "gemini-2.5-flash-lite"
```

To:

```python
    # LLM / AI — lite + standard tiers (open-source models)
    llm_together_api_key: str = ""
    llm_together_base_url: str = "https://api.together.xyz/v1"
    llm_together_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
    llm_groq_api_key: str = ""
    llm_groq_base_url: str = "https://api.groq.com/openai/v1"
    llm_groq_model: str = "llama-3.1-8b-instant"
    llm_lite_providers: str = "together,groq"
    llm_standard_providers: str = "together,groq"
```

Leave the premium settings (lines 24-27) unchanged.

- [ ] **Step 2: Update .env.example**

Add to the end of `backend/.env.example`:

```
# LLM — lite/standard tiers (open-source via Together AI / Groq)
LLM_TOGETHER_API_KEY=
LLM_GROQ_API_KEY=
# LLM — premium tier
LLM_PREMIUM_PROVIDER=openai
LLM_PREMIUM_API_KEY=
LLM_PREMIUM_MODEL=gpt-4o
```

- [ ] **Step 3: Verify config loads**

Run:
```bash
cd invest-ed/backend && python -c "from app.core.config import settings; print(settings.llm_together_model, settings.llm_groq_model)"
```

Expected: `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo llama-3.1-8b-instant`

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py .env.example
git commit -m "chore: add Together AI and Groq config, remove Gemini free-tier settings"
```

---

### Task 2: FallbackLLMClient and Tier-Based Routing

**Files:**
- Modify: `backend/app/services/llm_client.py`
- Modify: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Write failing tests for FallbackLLMClient**

Replace the entire contents of `tests/test_llm_client.py` with:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_client import (
    AnthropicClient,
    FallbackLLMClient,
    LLMError,
    OpenAIClient,
    get_llm_client,
    get_model_name,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_openai_client_complete():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"answer": 42}'

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result == '{"answer": 42}'
        mock_instance.chat.completions.create.assert_awaited_once()


async def test_anthropic_client_complete():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Hello there!"

    with patch("app.services.llm_client.AsyncAnthropic") as MockAnthropic:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        MockAnthropic.return_value = mock_instance

        client = AnthropicClient(api_key="test-key", model="claude-3-haiku-20240307")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )
        assert result == "Hello there!"
        mock_instance.messages.create.assert_awaited_once()


async def test_openai_client_raises_llm_error_on_failure():
    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        with pytest.raises(LLMError, match="API down"):
            await client.complete(
                system_prompt="You are helpful.",
                messages=[{"role": "user", "content": "Hi"}],
            )


async def test_fallback_client_uses_primary_when_healthy():
    primary = AsyncMock()
    primary.complete = AsyncMock(return_value="primary response")
    fallback = AsyncMock()
    fallback.complete = AsyncMock(return_value="fallback response")

    client = FallbackLLMClient(clients=[primary, fallback])
    result = await client.complete(
        system_prompt="test",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result == "primary response"
    primary.complete.assert_awaited_once()
    fallback.complete.assert_not_awaited()


async def test_fallback_client_falls_back_on_retryable_error():
    primary = AsyncMock()
    primary.complete = AsyncMock(side_effect=LLMError("rate limited", retryable=True))
    fallback = AsyncMock()
    fallback.complete = AsyncMock(return_value="fallback response")

    client = FallbackLLMClient(clients=[primary, fallback])
    result = await client.complete(
        system_prompt="test",
        messages=[{"role": "user", "content": "hi"}],
    )
    assert result == "fallback response"
    primary.complete.assert_awaited_once()
    fallback.complete.assert_awaited_once()


async def test_fallback_client_raises_on_non_retryable_error():
    primary = AsyncMock()
    primary.complete = AsyncMock(side_effect=LLMError("bad request", retryable=False))
    fallback = AsyncMock()

    client = FallbackLLMClient(clients=[primary, fallback])
    with pytest.raises(LLMError, match="bad request"):
        await client.complete(
            system_prompt="test",
            messages=[{"role": "user", "content": "hi"}],
        )
    fallback.complete.assert_not_awaited()


async def test_fallback_client_raises_last_error_when_all_fail():
    primary = AsyncMock()
    primary.complete = AsyncMock(side_effect=LLMError("primary down", retryable=True))
    fallback = AsyncMock()
    fallback.complete = AsyncMock(side_effect=LLMError("fallback down", retryable=True))

    client = FallbackLLMClient(clients=[primary, fallback])
    with pytest.raises(LLMError, match="fallback down"):
        await client.complete(
            system_prompt="test",
            messages=[{"role": "user", "content": "hi"}],
        )


def test_get_llm_client_returns_fallback_for_lite():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_lite_providers = "together,groq"
        mock_settings.llm_together_api_key = "tog-test"
        mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        mock_settings.llm_groq_api_key = "gsk-test"
        mock_settings.llm_groq_base_url = "https://api.groq.com/openai/v1"
        mock_settings.llm_groq_model = "llama-3.1-8b-instant"

        client = get_llm_client(tier="lite")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 2
        assert all(isinstance(c, OpenAIClient) for c in client.clients)


def test_get_llm_client_returns_fallback_for_standard():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_standard_providers = "together"
        mock_settings.llm_together_api_key = "tog-test"
        mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

        client = get_llm_client(tier="standard")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1


def test_get_llm_client_returns_premium_openai():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_premium_provider = "openai"
        mock_settings.llm_premium_api_key = "sk-test"
        mock_settings.llm_premium_model = "gpt-4o"

        client = get_llm_client(tier="premium")
        assert isinstance(client, OpenAIClient)


def test_get_llm_client_returns_premium_anthropic():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_premium_provider = "anthropic"
        mock_settings.llm_premium_api_key = "sk-ant-test"
        mock_settings.llm_premium_model = "claude-sonnet-4-20250514"

        client = get_llm_client(tier="premium")
        assert isinstance(client, AnthropicClient)


def test_get_llm_client_skips_providers_with_empty_key():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_lite_providers = "together,groq"
        mock_settings.llm_together_api_key = ""
        mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        mock_settings.llm_groq_api_key = "gsk-test"
        mock_settings.llm_groq_base_url = "https://api.groq.com/openai/v1"
        mock_settings.llm_groq_model = "llama-3.1-8b-instant"

        client = get_llm_client(tier="lite")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1  # Only Groq (Together key is empty)


def test_get_model_name():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        mock_settings.llm_premium_model = "gpt-4o"

        assert get_model_name("lite") == "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        assert get_model_name("standard") == "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        assert get_model_name("premium") == "gpt-4o"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_llm_client.py -v
```

Expected: Failures on `FallbackLLMClient`, `get_model_name`, and new `get_llm_client` tests (imports not found).

- [ ] **Step 3: Implement FallbackLLMClient and refactor get_llm_client**

Replace the entire contents of `app/services/llm_client.py` with:

```python
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
        raise last_error  # unreachable but satisfies type checker

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        last_error: LLMError | None = None
        for i, client in enumerate(self.clients):
            try:
                async for chunk in client.stream(
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
        raise last_error  # unreachable


def _is_retryable(exc: Exception | None) -> bool:
    """Check if an exception represents a retryable failure (rate limit / server error)."""
    if exc is None:
        return False
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    msg = str(exc).lower()
    return "rate" in msg or "timeout" in msg or "503" in msg or "502" in msg or "429" in msg


_PROVIDER_BUILDERS: dict[str, callable] = {}


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


_PROVIDER_BUILDERS = {
    "together": (_build_together_client, lambda: settings.llm_together_api_key),
    "groq": (_build_groq_client, lambda: settings.llm_groq_api_key),
}


def _build_chain(provider_csv: str) -> FallbackLLMClient:
    clients: list[LLMClient] = []
    for name in provider_csv.split(","):
        name = name.strip()
        if name not in _PROVIDER_BUILDERS:
            continue
        builder, get_key = _PROVIDER_BUILDERS[name]
        if not get_key():
            continue
        clients.append(builder())
    if not clients:
        raise ValueError(f"No valid providers configured in '{provider_csv}'")
    return FallbackLLMClient(clients=clients)


def get_model_name(tier: str = "lite") -> str:
    """Return the primary model name for a tier (for cache keys / logging)."""
    if tier == "premium":
        return settings.llm_premium_model
    return settings.llm_together_model


def get_llm_client(tier: str = "lite", *, premium: bool | None = None) -> LLMClient:
    """Return an LLM client for the given tier.

    Tiers:
      - "lite": simple tasks (news summaries, fun facts). Together AI → Groq fallback.
      - "standard": conversational tasks (chart coach, chart guide). Together AI → Groq fallback.
      - "premium": highest quality (tutor, quizzes). OpenAI or Anthropic.

    The deprecated `premium` kwarg is supported for backward compatibility:
      premium=True  → tier="premium"
      premium=False → tier="lite"
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_llm_client.py -v
```

Expected: All 14 tests pass.

- [ ] **Step 5: Run ruff to check for lint issues**

Run:
```bash
cd invest-ed/backend && ruff check app/services/llm_client.py tests/test_llm_client.py
```

Expected: Clean (no violations).

- [ ] **Step 6: Commit**

```bash
git add app/services/llm_client.py tests/test_llm_client.py
git commit -m "feat: add FallbackLLMClient and three-tier LLM routing (lite/standard/premium)"
```

---

### Task 3: Migrate Simulator Call Sites (lite + standard)

**Files:**
- Modify: `backend/app/routers/simulator.py`

There are 4 call sites in `simulator.py` to migrate:

| Line | Function | Current | New Tier |
|------|----------|---------|----------|
| ~197 | `_portfolio_news_summary` | `get_llm_client(premium=False)` | `tier="lite"` |
| ~255 | `_stock_news_summary` | `get_llm_client(premium=False)` | `tier="lite"` |
| ~321 | `_chart_guide` | `get_llm_client(premium=False)` | `tier="standard"` |
| ~455 | time machine fun fact | `get_llm_client(premium=False)` | `tier="lite"` |

- [ ] **Step 1: Replace all four call sites**

In `app/routers/simulator.py`, make these changes:

Change the portfolio news summary call (~line 197):
```python
# Before:
    llm = get_llm_client(premium=False)
# After:
    llm = get_llm_client(tier="lite")
```

Change the stock news summary call (~line 255):
```python
# Before:
    llm = get_llm_client(premium=False)
# After:
    llm = get_llm_client(tier="lite")
```

Change the chart guide call (~line 321):
```python
# Before:
    llm = get_llm_client(premium=False)
# After:
    llm = get_llm_client(tier="standard")
```

Change the time machine fun fact call (~line 455):
```python
# Before:
        llm = get_llm_client(premium=False)
# After:
        llm = get_llm_client(tier="lite")
```

- [ ] **Step 2: Run ruff check**

Run:
```bash
cd invest-ed/backend && ruff check app/routers/simulator.py
```

Expected: Clean.

- [ ] **Step 3: Run simulator tests**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_simulator.py -v
```

Expected: All 15 tests pass. (The tests mock the LLM layer, so the tier change is transparent.)

- [ ] **Step 4: Commit**

```bash
git add app/routers/simulator.py
git commit -m "refactor: migrate simulator LLM calls to tier-based routing"
```

---

### Task 4: Migrate Chart Coach Service (standard)

**Files:**
- Modify: `backend/app/services/chart_coach_service.py`

- [ ] **Step 1: Update the call site and model_name**

In `app/services/chart_coach_service.py`, make two changes:

Change the `model_name` assignment (line 98):
```python
# Before:
    model_name = settings.llm_free_model
# After:
    model_name = get_model_name("standard")
```

Add the import at the top — change line 13 from:
```python
from app.services.llm_client import get_llm_client
```
to:
```python
from app.services.llm_client import get_llm_client, get_model_name
```

Change the `get_llm_client` call (line 127):
```python
# Before:
    client = get_llm_client(premium=False)
# After:
    client = get_llm_client(tier="standard")
```

Remove the unused `settings` import from the top if `settings` is no longer used directly for model names. Check: `settings` is still used for `tutor_max_input_chars` and `tutor_max_messages_free` at lines 88 and 92, so keep the import.

- [ ] **Step 2: Run ruff check**

Run:
```bash
cd invest-ed/backend && ruff check app/services/chart_coach_service.py
```

Expected: Clean.

- [ ] **Step 3: Commit**

```bash
git add app/services/chart_coach_service.py
git commit -m "refactor: migrate chart coach to tier='standard' LLM routing"
```

---

### Task 5: Migrate Tutor Service (standard/premium)

**Files:**
- Modify: `backend/app/services/tutor_service.py`

- [ ] **Step 1: Update the call site and model_name**

In `app/services/tutor_service.py`, make these changes:

Change line 15 import from:
```python
from app.services.llm_client import get_llm_client
```
to:
```python
from app.services.llm_client import get_llm_client, get_model_name
```

Change the `model_name` assignment (line 109):
```python
# Before:
    model_name = settings.llm_premium_model if premium else settings.llm_free_model
# After:
    model_name = get_model_name("premium" if premium else "standard")
```

Change the `get_llm_client` call (line 147):
```python
# Before:
    client = get_llm_client(premium=premium)
# After:
    client = get_llm_client(tier="premium" if premium else "standard")
```

- [ ] **Step 2: Run ruff check**

Run:
```bash
cd invest-ed/backend && ruff check app/services/tutor_service.py
```

Expected: Clean.

- [ ] **Step 3: Commit**

```bash
git add app/services/tutor_service.py
git commit -m "refactor: migrate tutor service to tier-based LLM routing"
```

---

### Task 6: Migrate AI Content Service (standard/premium)

**Files:**
- Modify: `backend/app/services/ai_content_service.py`

- [ ] **Step 1: Update the call site**

In `app/services/ai_content_service.py`, change the import at line 14:
```python
# Before:
from app.services.llm_client import LLMError, get_llm_client
# After:
from app.services.llm_client import LLMError, get_llm_client, get_model_name
```

Change the `get_llm_client` call (line 85):
```python
# Before:
    client = get_llm_client(premium=premium)
# After:
    client = get_llm_client(tier="premium" if premium else "standard")
```

Check if `ai_content_service.py` uses `settings.llm_free_model` or `settings.llm_premium_model` anywhere for cache keys. If so, replace with `get_model_name()`. If not, no further changes needed.

- [ ] **Step 2: Run ruff check**

Run:
```bash
cd invest-ed/backend && ruff check app/services/ai_content_service.py
```

Expected: Clean.

- [ ] **Step 3: Run all tests to verify nothing is broken**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_llm_client.py tests/test_ai_content_service.py tests/test_auth.py tests/test_simulator.py -v
```

Expected: All pass.

- [ ] **Step 4: Commit**

```bash
git add app/services/ai_content_service.py
git commit -m "refactor: migrate AI content service to tier-based LLM routing"
```

---

### Task 7: End-to-End Verification

**Files:**
- No new files — verification only

- [ ] **Step 1: Run ruff across the entire backend**

Run:
```bash
cd invest-ed/backend && ruff check .
```

Expected: Clean (all checks passed).

- [ ] **Step 2: Run all backend tests**

Run:
```bash
cd invest-ed/backend && python -m pytest tests/test_llm_client.py tests/test_ai_content_service.py tests/test_auth.py tests/test_users.py tests/test_simulator.py -v
```

Expected: All pass (46+ tests).

- [ ] **Step 3: Run frontend type-check (no frontend changes but verify nothing broke)**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit
```

Expected: Clean.

- [ ] **Step 4: Verify `get_llm_client(premium=...)` backward compat still works**

Run:
```bash
cd invest-ed/backend && python -c "
from unittest.mock import patch, MagicMock
with patch('app.services.llm_client.settings') as s:
    s.llm_premium_provider = 'openai'
    s.llm_premium_api_key = 'test'
    s.llm_premium_model = 'gpt-4o'
    s.llm_lite_providers = 'together'
    s.llm_together_api_key = 'test'
    s.llm_together_base_url = 'https://api.together.xyz/v1'
    s.llm_together_model = 'llama-3.1-8b'
    from app.services.llm_client import get_llm_client, OpenAIClient, FallbackLLMClient
    assert isinstance(get_llm_client(premium=True), OpenAIClient)
    assert isinstance(get_llm_client(premium=False), FallbackLLMClient)
    print('Backward compat OK')
"
```

Expected: `Backward compat OK`

- [ ] **Step 5: Verify no references to old settings remain**

Run:
```bash
cd invest-ed/backend && grep -rn "llm_free_" app/ tests/ --include="*.py"
```

Expected: No results (all references to `llm_free_api_key`, `llm_free_base_url`, `llm_free_model` have been removed).
