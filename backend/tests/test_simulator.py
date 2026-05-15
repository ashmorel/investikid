from decimal import Decimal

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _login(client, email="trader@example.com", username="trader", country_code="GB", currency_code="GBP"):
    payload = {
        **_USER_BASE, "email": email, "username": username,
        "country_code": country_code, "currency_code": currency_code,
    }
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_portfolio_starts_with_virtual_cash(client):
    await _login(client)
    r = await client.get("/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["virtual_cash"]) == Decimal("1000.00")
    assert body["currency_code"] == "GBP"
    assert body["holdings"] == []


async def test_market_search_returns_matches(client):
    await _login(client)
    r = await client.get("/market/search?q=APP")
    assert r.status_code == 200
    tickers = [row["ticker"] for row in r.json()]
    assert "AAPL" in tickers


async def test_buy_trade_decreases_cash_adds_holding(client):
    await _login(client)
    payload = {"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"}
    r = await client.post("/portfolio/trades", json=payload)
    assert r.status_code == 201
    pf = (await client.get("/portfolio")).json()
    # VOD at 0.72 x 10 = 7.20
    assert Decimal(pf["virtual_cash"]) == Decimal("1000.00") - Decimal("7.20")
    assert len(pf["holdings"]) == 1
    assert pf["holdings"][0]["ticker"] == "VOD"
    assert Decimal(pf["holdings"][0]["shares"]) == Decimal("10")


async def test_sell_trade_increases_cash_removes_holding(client):
    await _login(client)
    await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"})
    r = await client.post(
        "/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "sell", "shares": "10"}
    )
    assert r.status_code == 201
    pf = (await client.get("/portfolio")).json()
    assert Decimal(pf["virtual_cash"]) == Decimal("1000.00")
    assert pf["holdings"] == []


async def test_insufficient_funds_rejected(client):
    await _login(client)
    r = await client.post(
        "/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "100000"}
    )
    assert r.status_code == 400


async def test_insufficient_shares_rejected(client):
    await _login(client)
    r = await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "sell", "shares": "1"})
    assert r.status_code == 400


async def test_unknown_ticker_rejected(client):
    await _login(client)
    r = await client.post("/portfolio/trades", json={"ticker": "NOPE", "exchange": "LSE", "type": "buy", "shares": "1"})
    assert r.status_code == 404  # ticker not found in static provider


async def test_trade_history_listed_newest_first(client):
    await _login(client)
    await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "1"})
    await client.post("/portfolio/trades", json={"ticker": "BP", "exchange": "LSE", "type": "buy", "shares": "1"})
    r = await client.get("/portfolio/trades")
    assert r.status_code == 200
    trades = r.json()
    assert len(trades) == 2
    assert trades[0]["ticker"] == "BP"  # newest first


async def test_trade_awards_first_trade_badge(client, db_session):
    from app.models.gamification import Badge
    db_session.add(Badge(
        name="First Trade", description="x", icon_url="/x.svg",
        condition_type="trade_count", condition_value=1,
    ))
    await db_session.commit()

    await _login(client)
    await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "1"})

    badges = (await client.get("/users/me/badges")).json()
    assert any(b["name"] == "First Trade" for b in badges)


async def test_portfolio_history_empty_when_no_trades(client):
    await _login(client, email="hist@example.com", username="histuser")
    r = await client.get("/portfolio/history")
    assert r.status_code == 200
    assert r.json() == []


async def test_portfolio_history_returns_snapshots_after_trades(client):
    await _login(client, email="hist2@example.com", username="hist2user")
    # Make two trades
    await client.post("/portfolio/trades", json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"})
    await client.post("/portfolio/trades", json={"ticker": "BP", "exchange": "LSE", "type": "buy", "shares": "5"})

    r = await client.get("/portfolio/history")
    assert r.status_code == 200
    history = r.json()
    assert len(history) >= 1
    # Each entry has date and value
    for entry in history:
        assert "date" in entry
        assert "value" in entry
        assert isinstance(entry["value"], (int, float))
    # The last entry's value should match current portfolio total_value
    pf = (await client.get("/portfolio")).json()
    assert abs(history[-1]["value"] - float(pf["total_value"])) < 0.02


async def test_time_machine_returns_periods(client):
    await _login(client)
    r = await client.get("/market/time-machine/NASDAQ/AAPL")
    assert r.status_code == 200
    body = r.json()
    assert body["ticker"] == "AAPL"
    assert isinstance(body["periods"], list)
    # Static provider may return empty periods (no max history) — just check shape
    assert "fun_fact" in body


async def test_time_machine_unknown_ticker(client):
    await _login(client, email="tm2@example.com", username="tm2")
    r = await client.get("/market/time-machine/NASDAQ/ZZZZZZ")
    assert r.status_code == 200
    body = r.json()
    assert body["periods"] == []


async def test_tips_returns_list(client):
    await _login(client, email="tips@example.com", username="tipster")
    r = await client.get("/market/tips")
    assert r.status_code == 200
    tips = r.json()
    assert len(tips) >= 1
    for tip in tips:
        assert "id" in tip
        assert "title" in tip
        assert "description" in tip
        assert "example_ticker" in tip
        assert "example_exchange" in tip


async def test_chart_coach_requires_auth(client):
    r = await client.post("/market/chart-coach", json={
        "ticker": "AAPL", "exchange": "NASDAQ", "period": "1mo", "message": "What does this chart show?"
    })
    assert r.status_code == 403
