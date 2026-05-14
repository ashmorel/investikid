from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_client import (
    AnthropicClient,
    LLMError,
    OpenAIClient,
    get_llm_client,
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


def test_get_llm_client_returns_correct_provider():
    with patch("app.services.llm_client.settings") as mock_settings:
        # Free tier uses Gemini Flash via OpenAI-compatible API
        mock_settings.llm_free_api_key = "AIza-test"
        mock_settings.llm_free_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        mock_settings.llm_free_model = "gemini-2.5-flash-lite"
        # Premium tier uses OpenAI
        mock_settings.llm_premium_provider = "openai"
        mock_settings.llm_premium_api_key = "sk-test"
        mock_settings.llm_premium_model = "gpt-4o"

        free_client = get_llm_client(premium=False)
        assert isinstance(free_client, OpenAIClient)

        premium_client = get_llm_client(premium=True)
        assert isinstance(premium_client, OpenAIClient)

    # Premium with Anthropic provider
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.llm_free_api_key = "AIza-test"
        mock_settings.llm_free_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        mock_settings.llm_free_model = "gemini-2.5-flash-lite"
        mock_settings.llm_premium_provider = "anthropic"
        mock_settings.llm_premium_api_key = "sk-ant-test"
        mock_settings.llm_premium_model = "claude-sonnet-4-20250514"

        anthropic_client = get_llm_client(premium=True)
        assert isinstance(anthropic_client, AnthropicClient)
