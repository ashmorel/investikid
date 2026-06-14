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
        mock_settings.llm_together_model = "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
        mock_settings.llm_premium_model = "gpt-4o"

        assert get_model_name("lite") == "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
        assert get_model_name("standard") == "meta-llama/Meta-Llama-3-8B-Instruct-Lite"
        assert get_model_name("premium") == "gpt-4o"
