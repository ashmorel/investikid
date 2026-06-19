import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.content import Level, Module
from app.models.market import Market
from app.models.market_brief import MarketBrief

pytestmark = pytest.mark.asyncio(loop_scope="session")

US_BRIEF = {
    "currency": "USD",
    "tax_advantaged_accounts": ["Roth IRA", "529 plan"],
    "regulators": ["SEC", "FINRA"],
    "deposit_protection": "FDIC insures up to $250,000",
    "typical_products": ["savings account"],
    "local_examples": ["allowance in a piggy bank"],
    "notes": "Dollars and cents.",
}

# The mocked premium model returns a JSON array of suggestions.
US_SUGGESTIONS = json.dumps(
    [
        {
            "title": "529 College Savings",
            "topic": "saving",
            "rationale": "US-specific tax-advantaged education savings.",
            "action": "add",
            "replaces": None,
            "suggested_concepts": ["What is a 529", "Tax benefits", "How to open one"],
        },
        {
            "title": "US Banking Basics",
            "topic": "banking",
            "rationale": "Replace the UK-regulator module with US equivalents.",
            "action": "replace",
            "replaces": "GB Saving",
            "suggested_concepts": ["FDIC", "Checking vs savings"],
        },
    ]
)


async def _seed_gb_module(db_session):
    module = Module(
        topic="savings", title="GB Saving", country_codes=[], is_premium=False,
        order_index=900, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="GB Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return module


async def _seed_us_market(db_session):
    # The US market is seeded globally by the test suite; reuse it if present.
    market = await db_session.get(Market, "US")
    if market is None:
        market = Market(code="US", name="United States", currency_code="USD")
        db_session.add(market)
        await db_session.flush()
    return market


async def test_module_suggestions_returns_list(admin_client, db_session):
    await _seed_gb_module(db_session)
    await _seed_us_market(db_session)
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified"))
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=US_SUGGESTIONS)
    with patch("app.services.market_module_suggester.get_llm_client",
               return_value=mock_client):
        resp = await admin_client.post("/admin/markets/US/module-suggestions")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    for item in body:
        assert set(item.keys()) >= {
            "title", "topic", "rationale", "action", "replaces", "suggested_concepts",
        }
    # The system prompt is grounded in the GB titles + the verified brief.
    system_prompt = mock_client.complete.await_args.kwargs["system_prompt"]
    assert "GB Saving" in system_prompt
    assert "USD" in system_prompt


async def test_module_suggestions_requires_verified_brief(admin_client, db_session):
    await _seed_gb_module(db_session)
    await _seed_us_market(db_session)
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="draft"))
    await db_session.flush()

    resp = await admin_client.post("/admin/markets/US/module-suggestions")
    assert resp.status_code == 409, resp.text


async def test_module_suggestions_malformed_llm_returns_empty(admin_client, db_session):
    await _seed_gb_module(db_session)
    await _seed_us_market(db_session)
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified"))
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="not json")
    with patch("app.services.market_module_suggester.get_llm_client",
               return_value=mock_client):
        resp = await admin_client.post("/admin/markets/US/module-suggestions")

    assert resp.status_code == 200, resp.text
    assert resp.json() == []
