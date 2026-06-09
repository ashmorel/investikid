import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import tips_service
from app.services.tips_service import generate_personalised_tips, learning_stage


def test_learning_stage_buckets():
    assert learning_stage(0) == "new"
    assert learning_stage(1) == "beginner"
    assert learning_stage(5) == "beginner"
    assert learning_stage(6) == "intermediate"
    assert learning_stage(15) == "intermediate"
    assert learning_stage(16) == "advanced"
    assert learning_stage(999) == "advanced"


_TWO_TIPS = json.dumps([
    {"id": "p1", "title": "Your Apple Stock", "description": "Since you own Apple, here's a tip about tech.", "example_ticker": "AAPL", "example_exchange": "NASDAQ"},
    {"id": "p2", "title": "Spread It Out", "description": "You're learning diversification — try different industries.", "example_ticker": "KO", "example_exchange": "NYSE"},
])


@pytest.fixture(autouse=True)
def _clear_cache():
    tips_service._personal_cache.clear()
    yield
    tips_service._personal_cache.clear()


@pytest.mark.asyncio
async def test_personalised_tips_generated_and_flagged():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    assert was_unsafe is False
    assert len(tips) == 2
    assert all(t.personalised for t in tips)
    assert tips[0].example_ticker == "AAPL"


@pytest.mark.asyncio
async def test_personalised_tips_empty_when_no_context():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc:
        tips, was_unsafe = await generate_personalised_tips(user_id=1, holdings=[], stage="new", age=10)
    assert tips == []
    assert was_unsafe is False
    gc.assert_not_called()


@pytest.mark.asyncio
async def test_personalised_tips_unsafe_returns_empty_flagged():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=False, text="", category="advice"))):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    assert tips == []
    assert was_unsafe is True


@pytest.mark.asyncio
async def test_personalised_tips_error_returns_empty_not_unsafe():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(side_effect=RuntimeError("llm down"))
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client):
        tips, was_unsafe = await generate_personalised_tips(
            user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12,
        )
    assert tips == []
    assert was_unsafe is False


@pytest.mark.asyncio
async def test_personalised_tips_cache_hit():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc, \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        a, _ = await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
        b, _ = await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
    assert a == b
    assert gc.call_count == 1


@pytest.mark.asyncio
async def test_personalised_tips_refresh_bypasses_cache():
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_TWO_TIPS)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client) as gc, \
         patch("app.services.tips_service.moderate_output", new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12)
        await generate_personalised_tips(user_id=1, holdings=[("AAPL", "Apple Inc.")], stage="beginner", age=12, refresh=True)
    assert gc.call_count == 2
