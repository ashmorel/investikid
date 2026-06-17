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


async def test_openai_client_records_token_usage():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.usage.prompt_tokens = 120
    mock_response.usage.completion_tokens = 30

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI, \
            patch("app.services.llm_client.record_usage") as mock_record:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="k", model="llama-3", provider="together")
        await client.complete(system_prompt="s", messages=[{"role": "user", "content": "hi"}])

        mock_record.assert_called_once_with(
            provider="together", model="llama-3", prompt_tokens=120, completion_tokens=30
        )


async def test_anthropic_client_records_token_usage():
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "ok"
    mock_response.usage.input_tokens = 200
    mock_response.usage.output_tokens = 50

    with patch("app.services.llm_client.AsyncAnthropic") as MockAnthropic, \
            patch("app.services.llm_client.record_usage") as mock_record:
        mock_instance = AsyncMock()
        mock_instance.messages.create = AsyncMock(return_value=mock_response)
        MockAnthropic.return_value = mock_instance

        client = AnthropicClient(api_key="k", model="claude-x", provider="anthropic-premium")
        await client.complete(system_prompt="s", messages=[{"role": "user", "content": "hi"}])

        mock_record.assert_called_once_with(
            provider="anthropic-premium", model="claude-x", prompt_tokens=200, completion_tokens=50
        )


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
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
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
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"

        client = get_llm_client(tier="standard")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1


def test_get_llm_client_returns_premium_openai():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_premium_provider = "openai"
        mock_settings.llm_premium_api_key = "sk-test"
        mock_settings.llm_premium_model = "gpt-4o"
        mock_settings.llm_standard_providers = "together"
        mock_settings.llm_together_api_key = ""  # no fallback configured

        client = get_llm_client(tier="premium")
        # Premium is a fallback chain led by the premium provider.
        assert isinstance(client, FallbackLLMClient)
        assert isinstance(client.clients[0], OpenAIClient)


def test_get_llm_client_returns_premium_anthropic():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_premium_provider = "anthropic"
        mock_settings.llm_premium_api_key = "sk-ant-test"
        mock_settings.llm_premium_model = "claude-sonnet-4-20250514"
        mock_settings.llm_standard_providers = "together"
        mock_settings.llm_together_api_key = ""  # no fallback configured

        client = get_llm_client(tier="premium")
        assert isinstance(client, FallbackLLMClient)
        assert isinstance(client.clients[0], AnthropicClient)


def test_premium_falls_back_to_standard_provider():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_premium_provider = "openai"
        mock_settings.llm_premium_api_key = "sk-test"
        mock_settings.llm_premium_model = "gpt-4o"
        mock_settings.llm_standard_providers = "together"
        mock_settings.llm_together_api_key = "tg-test"
        mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"

        client = get_llm_client(tier="premium")
        # OpenAI premium first, Together as fallback.
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 2
        assert isinstance(client.clients[0], OpenAIClient)
        assert isinstance(client.clients[1], OpenAIClient)  # Together via OpenAI SDK


def test_get_llm_client_skips_providers_with_empty_key():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_lite_providers = "together,groq"
        mock_settings.llm_together_api_key = ""
        mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
        mock_settings.llm_groq_api_key = "gsk-test"
        mock_settings.llm_groq_base_url = "https://api.groq.com/openai/v1"
        mock_settings.llm_groq_model = "llama-3.1-8b-instant"

        client = get_llm_client(tier="lite")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1


async def test_fallback_client_with_no_providers_raises_llm_error():
    client = FallbackLLMClient(clients=[])
    with pytest.raises(LLMError):
        await client.complete(
            system_prompt="x",
            messages=[{"role": "user", "content": "hi"}],
        )


def test_get_model_name():
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_gemini_flash_lite_model = "gemini-2.5-flash-lite"
        mock_settings.llm_gemini_flash_model = "gemini-2.5-flash"
        mock_settings.llm_premium_model = "gpt-5-mini"

        assert get_model_name("lite") == "gemini-2.5-flash-lite"
        assert get_model_name("standard") == "gemini-2.5-flash"
        assert get_model_name("premium") == "gpt-5-mini"


def _mock_settings_for_gemini(mock_settings, *, gemini_key: str, together_key: str = "") -> None:
    """Apply all settings attributes needed for Gemini provider tests."""
    mock_settings.llm_gemini_api_key = gemini_key
    mock_settings.llm_gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    mock_settings.llm_gemini_flash_lite_model = "gemini-2.5-flash-lite"
    mock_settings.llm_gemini_flash_model = "gemini-2.5-flash"
    mock_settings.llm_together_api_key = together_key
    mock_settings.llm_together_base_url = "https://api.together.xyz/v1"
    mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"


def test_get_llm_client_lite_gemini_primary_with_together_fallback():
    """When Gemini key is set, lite chain has Gemini first and Together second."""
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_lite_providers = "gemini_flash_lite,together"
        _mock_settings_for_gemini(mock_settings, gemini_key="gm-key", together_key="tog-key")

        client = get_llm_client(tier="lite")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 2
        first = client.clients[0]
        second = client.clients[1]
        assert isinstance(first, OpenAIClient)
        assert first._provider == "gemini"
        assert first._model == "gemini-2.5-flash-lite"
        assert isinstance(second, OpenAIClient)
        assert second._provider == "together"


def test_get_llm_client_standard_gemini_primary_with_together_fallback():
    """When Gemini key is set, standard chain has Gemini Flash first and Together second."""
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_standard_providers = "gemini_flash,together"
        _mock_settings_for_gemini(mock_settings, gemini_key="gm-key", together_key="tog-key")

        client = get_llm_client(tier="standard")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 2
        first = client.clients[0]
        assert isinstance(first, OpenAIClient)
        assert first._provider == "gemini"
        assert first._model == "gemini-2.5-flash"
        second = client.clients[1]
        assert isinstance(second, OpenAIClient)
        assert second._provider == "together"


def test_get_llm_client_gemini_key_empty_falls_back_to_together():
    """When Gemini key is absent (CI/local), Gemini is skipped and Together serves."""
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_lite_providers = "gemini_flash_lite,together"
        _mock_settings_for_gemini(mock_settings, gemini_key="", together_key="tog-key")

        client = get_llm_client(tier="lite")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1
        assert isinstance(client.clients[0], OpenAIClient)
        assert client.clients[0]._provider == "together"


def test_gemini_client_targets_gemini_base_url():
    """The Gemini OpenAIClient is constructed with the Gemini base URL."""
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_standard_providers = "gemini_flash"
        _mock_settings_for_gemini(mock_settings, gemini_key="gm-key")

        client = get_llm_client(tier="standard")
        assert isinstance(client, FallbackLLMClient)
        assert len(client.clients) == 1
        gemini_client = client.clients[0]
        assert isinstance(gemini_client, OpenAIClient)
        # The underlying AsyncOpenAI client stores base_url; verify via provider + model
        assert gemini_client._provider == "gemini"
        assert gemini_client._model == "gemini-2.5-flash"


async def test_fallback_falls_through_on_auth_error():
    """A 401 (bad API key) on provider 0 should fall through to provider 1, not raise."""

    class AuthError(Exception):
        status_code = 401

    err = LLMError("unauthorized", retryable=False)
    err.__cause__ = AuthError()

    bad = AsyncMock()
    bad.complete = AsyncMock(side_effect=err)

    good = AsyncMock()
    good.complete = AsyncMock(return_value="ok")

    client = FallbackLLMClient(clients=[bad, good])
    result = await client.complete(
        system_prompt="s",
        messages=[{"role": "user", "content": "x"}],
    )
    assert result == "ok"
    good.complete.assert_awaited_once()


async def test_fallback_falls_through_on_403_auth_error():
    """A 403 (forbidden/bad key) on provider 0 should fall through to provider 1."""

    class ForbiddenError(Exception):
        status_code = 403

    err = LLMError("forbidden", retryable=False)
    err.__cause__ = ForbiddenError()

    bad = AsyncMock()
    bad.complete = AsyncMock(side_effect=err)

    good = AsyncMock()
    good.complete = AsyncMock(return_value="fallback result")

    client = FallbackLLMClient(clients=[bad, good])
    result = await client.complete(
        system_prompt="s",
        messages=[{"role": "user", "content": "x"}],
    )
    assert result == "fallback result"
    good.complete.assert_awaited_once()


async def test_fallback_auth_error_on_last_provider_still_raises():
    """A 401 on the last (only) provider must still propagate — no more fallbacks."""

    class AuthError(Exception):
        status_code = 401

    err = LLMError("unauthorized", retryable=False)
    err.__cause__ = AuthError()

    only_bad = AsyncMock()
    only_bad.complete = AsyncMock(side_effect=err)

    client = FallbackLLMClient(clients=[only_bad])
    with pytest.raises(LLMError, match="unauthorized"):
        await client.complete(
            system_prompt="s",
            messages=[{"role": "user", "content": "x"}],
        )


async def test_fallback_non_auth_non_retryable_still_raises_immediately():
    """A generic 400 (bad request, non-auth) on provider 0 must raise immediately
    without trying provider 1 — this is the existing contract."""
    bad = AsyncMock()
    bad.complete = AsyncMock(side_effect=LLMError("bad request", retryable=False))
    good = AsyncMock()
    good.complete = AsyncMock(return_value="should not reach")

    client = FallbackLLMClient(clients=[bad, good])
    with pytest.raises(LLMError, match="bad request"):
        await client.complete(
            system_prompt="s",
            messages=[{"role": "user", "content": "x"}],
        )
    good.complete.assert_not_awaited()


# ---------------------------------------------------------------------------
# Reasoning-model kwarg tests (GPT-5 / o-series fix)
# ---------------------------------------------------------------------------


async def test_openai_complete_reasoning_model_uses_max_completion_tokens():
    """gpt-5-mini must use max_completion_tokens and omit max_tokens + temperature."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "reasoning answer"
    mock_response.usage = None

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-5-mini")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=800,
            temperature=0.7,
        )
        assert result == "reasoning answer"
        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_completion_tokens"] == 800
        assert "max_tokens" not in call_kwargs
        assert "temperature" not in call_kwargs


async def test_openai_complete_normal_model_uses_max_tokens():
    """gpt-4o-mini (non-reasoning) must use max_tokens + temperature unchanged."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "normal answer"
    mock_response.usage = None

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=600,
            temperature=0.4,
        )
        assert result == "normal answer"
        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 600
        assert call_kwargs["temperature"] == 0.4
        assert "max_completion_tokens" not in call_kwargs


async def test_openai_complete_gemini_model_uses_max_tokens():
    """gemini-2.5-flash via the OpenAI-compat shim must use max_tokens + temperature."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "gemini answer"
    mock_response.usage = None

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(
            api_key="gm-key",
            model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            provider="gemini",
        )
        result = await client.complete(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=400,
            temperature=0.3,
        )
        assert result == "gemini answer"
        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 400
        assert call_kwargs["temperature"] == 0.3
        assert "max_completion_tokens" not in call_kwargs


async def test_openai_stream_reasoning_model_uses_max_completion_tokens():
    """gpt-5-mini stream must use max_completion_tokens and omit max_tokens + temperature."""

    async def fake_stream():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "hi"
        yield chunk

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=fake_stream())
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-5-mini")
        chunks = []
        async for chunk in client.stream(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=800,
            temperature=0.7,
        ):
            chunks.append(chunk)

        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_completion_tokens"] == 800
        assert "max_tokens" not in call_kwargs
        assert "temperature" not in call_kwargs
        assert call_kwargs.get("stream") is True


async def test_openai_stream_normal_model_uses_max_tokens():
    """gpt-4o-mini stream must use max_tokens + temperature unchanged."""

    async def fake_stream():
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = "hi"
        yield chunk

    with patch("app.services.llm_client.AsyncOpenAI") as MockOpenAI:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=fake_stream())
        MockOpenAI.return_value = mock_instance

        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        chunks = []
        async for chunk in client.stream(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=600,
            temperature=0.4,
        ):
            chunks.append(chunk)

        call_kwargs = mock_instance.chat.completions.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 600
        assert call_kwargs["temperature"] == 0.4
        assert "max_completion_tokens" not in call_kwargs
        assert call_kwargs.get("stream") is True
