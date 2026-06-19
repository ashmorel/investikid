import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.market_brief import MarketBrief
from app.services.market_brief_service import require_verified_brief

pytestmark = pytest.mark.asyncio(loop_scope="session")

BRIEF = json.dumps({
    "currency": "USD",
    "tax_advantaged_accounts": ["529 plan", "Roth IRA"],
    "regulators": ["SEC", "FINRA"],
    "deposit_protection": "FDIC insures up to $250,000",
    "typical_products": ["savings account", "brokerage account"],
    "local_examples": ["allowance saved in a piggy bank"],
    "notes": "Dollars and cents.",
})


def _mock_client():
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=BRIEF)
    return mock_client


async def test_generate_brief_creates_draft(admin_client):
    with patch("app.services.market_brief_service.get_llm_client", return_value=_mock_client()):
        resp = await admin_client.post("/admin/markets/US/brief/generate")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["market_code"] == "US"
    assert body["brief_json"]["currency"] == "USD"
    assert "tax_advantaged_accounts" in body["brief_json"]
    assert "regulators" in body["brief_json"]


async def test_update_brief_persists(admin_client):
    with patch("app.services.market_brief_service.get_llm_client", return_value=_mock_client()):
        await admin_client.post("/admin/markets/US/brief/generate")
    edited = {"currency": "USD", "notes": "edited by a human"}
    resp = await admin_client.put("/admin/markets/US/brief", json={"brief_json": edited})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["brief_json"]["notes"] == "edited by a human"
    assert body["status"] == "draft"

    got = await admin_client.get("/admin/markets/US/brief")
    assert got.status_code == 200
    assert got.json()["brief_json"]["notes"] == "edited by a human"


async def test_verify_brief_sets_status(admin_client):
    with patch("app.services.market_brief_service.get_llm_client", return_value=_mock_client()):
        await admin_client.post("/admin/markets/US/brief/generate")
    resp = await admin_client.post("/admin/markets/US/brief/verify")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "verified"


async def test_require_verified_brief(db_session):
    # Absent → 409
    with pytest.raises(HTTPException) as exc:
        await require_verified_brief(db_session, "AU")
    assert exc.value.status_code == 409

    # Draft → 409
    db_session.add(MarketBrief(market_code="AU", brief_json={"currency": "AUD"}, status="draft"))
    await db_session.flush()
    with pytest.raises(HTTPException) as exc:
        await require_verified_brief(db_session, "AU")
    assert exc.value.status_code == 409

    # Verified → returns the brief
    brief = await db_session.get(MarketBrief, "AU")
    brief.status = "verified"
    await db_session.flush()
    got = await require_verified_brief(db_session, "AU")
    assert got.market_code == "AU"
    assert got.status == "verified"


async def test_generate_brief_retries_then_succeeds(admin_client):
    # First LLM call raises (transient), second returns a valid brief → 200.
    flaky = AsyncMock()
    flaky.complete = AsyncMock(side_effect=[RuntimeError("upstream 503"), BRIEF])
    with patch("app.services.market_brief_service.get_llm_client", return_value=flaky):
        resp = await admin_client.post("/admin/markets/CA/brief/generate")
    assert resp.status_code == 200, resp.text
    assert resp.json()["brief_json"]["currency"] == "USD"
    assert flaky.complete.await_count == 2


async def test_generate_brief_empty_response_retries(admin_client):
    # An empty completion is treated as a failure and retried.
    flaky = AsyncMock()
    flaky.complete = AsyncMock(side_effect=["", BRIEF])
    with patch("app.services.market_brief_service.get_llm_client", return_value=flaky):
        resp = await admin_client.post("/admin/markets/IE/brief/generate")
    assert resp.status_code == 200, resp.text
    assert flaky.complete.await_count == 2


async def test_generate_brief_persistent_failure_returns_502(admin_client):
    # Every attempt raises → BriefGenerationError → clean 502 (not an opaque 500).
    broken = AsyncMock()
    broken.complete = AsyncMock(side_effect=RuntimeError("auth failed"))
    with patch("app.services.market_brief_service.get_llm_client", return_value=broken):
        resp = await admin_client.post("/admin/markets/AU/brief/generate")
    assert resp.status_code == 502, resp.text


async def test_generate_unknown_market_404(admin_client):
    with patch("app.services.market_brief_service.get_llm_client", return_value=_mock_client()):
        resp = await admin_client.post("/admin/markets/ZZ/brief/generate")
    assert resp.status_code == 404
