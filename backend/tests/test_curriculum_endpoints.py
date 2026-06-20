# backend/tests/test_curriculum_endpoints.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.market_brief import MarketBrief

pytestmark = pytest.mark.asyncio(loop_scope="session")

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _tree():
    levels = [{"title": f"L{i}", "order_index": i, "complexity_tier": 1 + i // 3,
               "learning_objective": "o", "concepts": ["c"], "backbone_keys": [k]}
              for i, k in enumerate(ALL)]
    return {"modules": [{"topic": "money", "title": "Money", "icon": "💵",
                         "min_age": 10, "max_age": 14, "order_index": 0, "levels": levels}]}

async def _seed_verified_brief(db_session):
    # Market(code="US") is already seeded by seed_markets_once; only add the brief.
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="verified"))
    await db_session.flush()

async def _seed_draft_brief(db_session):
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="draft"))
    await db_session.flush()

async def test_design_then_accept_flow(admin_client, db_session):
    await _seed_verified_brief(db_session)
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps(_tree()))
    with patch("app.services.market_curriculum.designer.get_llm_client", return_value=client):
        r = await admin_client.post("/admin/markets/US/curriculum/design")
    assert r.status_code == 200, r.text
    assert r.json()["coverage"]["ok"] is True
    g = await admin_client.get("/admin/markets/US/curriculum")
    assert g.status_code == 200 and len(g.json()["proposal"]["modules"]) == 1
    a = await admin_client.post("/admin/markets/US/curriculum/accept")
    assert a.status_code == 200 and a.json() == {"modules": 1, "levels": 9}

async def test_design_unverified_brief_409(admin_client, db_session):
    await _seed_draft_brief(db_session)
    r = await admin_client.post("/admin/markets/US/curriculum/design")
    assert r.status_code == 409, r.text

async def test_get_curriculum_404_when_none(admin_client):
    r = await admin_client.get("/admin/markets/ZZ/curriculum")
    assert r.status_code == 404
