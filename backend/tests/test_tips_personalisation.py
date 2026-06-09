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
    tips_service._generic_cache.clear()
    yield
    tips_service._personal_cache.clear()
    tips_service._generic_cache.clear()


# --- Endpoint tests (Task 4) ----------------------------------------------

# _login helper mirrored from tests/test_simulator.py.
_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _login(client, email="tipster@example.com", username="tipster"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(_REGISTER_URL, json=payload)
    await client.post(_LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


_SIX_GENERIC = json.dumps([
    {"id": "g1", "title": "Start Small", "description": "You don't need much to begin investing.", "example_ticker": "AAPL", "example_exchange": "NASDAQ"},
    {"id": "g2", "title": "Spread It Out", "description": "Owning different companies lowers your risk.", "example_ticker": "KO", "example_exchange": "NYSE"},
    {"id": "g3", "title": "Think Long Term", "description": "Investing works best over many years.", "example_ticker": "MSFT", "example_exchange": "NASDAQ"},
    {"id": "g4", "title": "Know What You Own", "description": "Pick companies you understand and like.", "example_ticker": "DIS", "example_exchange": "NYSE"},
    {"id": "g5", "title": "Be Patient", "description": "Prices go up and down — that's normal.", "example_ticker": "NKE", "example_exchange": "NYSE"},
    {"id": "g6", "title": "Keep Learning", "description": "The more you learn, the better you invest.", "example_ticker": "GOOGL", "example_exchange": "NASDAQ"},
])


@pytest.mark.asyncio(loop_scope="session")
async def test_tips_endpoint_generic_when_no_context(client):
    tips_service._generic_cache.clear()
    tips_service._personal_cache.clear()
    await _login(client, email="tipsgeneric@example.com", username="tipsgeneric")

    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_SIX_GENERIC)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output",
               new=AsyncMock(return_value=MagicMock(safe=True, text="ok", category=None))):
        r = await client.get("/market/tips")

    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 3
    assert all(t["personalised"] is False for t in body)


@pytest.mark.asyncio(loop_scope="session")
async def test_tips_endpoint_unsafe_personalised_audited(client, db_session):
    from sqlalchemy import select

    from app.models.audit import AuditLog

    tips_service._generic_cache.clear()
    tips_service._personal_cache.clear()
    await _login(client, email="tipsunsafe@example.com", username="tipsunsafe")
    # A holding gives the personalised generator context to run.
    await client.post(
        "/portfolio/trades",
        json={"ticker": "AAPL", "exchange": "NASDAQ", "type": "buy", "shares": "1"},
    )

    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value=_SIX_GENERIC)
    with patch("app.services.tips_service.get_llm_client", return_value=mock_client), \
         patch("app.services.tips_service.moderate_output",
               new=AsyncMock(return_value=MagicMock(safe=False, text="", category="advice"))):
        r = await client.get("/market/tips")

    assert r.status_code == 200
    body = r.json()
    assert all(t["personalised"] is False for t in body)

    rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.event_type == "moderation_block")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].metadata_json["surface"] == "tips"


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
