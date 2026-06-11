from decimal import Decimal

import pytest

from app.services.app_settings import (
    get_trade_commission_pct,
    set_trade_commission_pct,
)
from app.services.price_provider import PriceQuote
from app.services.simulator_service import InsufficientFundsError, execute_trade

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


async def _login(client, email="feetrader@example.com", username="feetrader"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


# ── app_settings ────────────────────────────────────────────────────


async def test_default_commission_pct_when_unset(db_session):
    pct = await get_trade_commission_pct(db_session)
    assert pct == Decimal("1.0")


async def test_set_then_get_commission_roundtrip(db_session):
    await set_trade_commission_pct(db_session, Decimal("2.5"))
    assert await get_trade_commission_pct(db_session) == Decimal("2.5")


@pytest.mark.parametrize("bad", [Decimal("-0.5"), Decimal("10.01"), Decimal("11")])
async def test_set_commission_out_of_bounds_rejected(db_session, bad):
    with pytest.raises(ValueError):
        await set_trade_commission_pct(db_session, bad)


@pytest.mark.parametrize("ok", [Decimal("0"), Decimal("10")])
async def test_set_commission_boundary_values_accepted(db_session, ok):
    await set_trade_commission_pct(db_session, ok)
    assert await get_trade_commission_pct(db_session) == ok


# ── trade execution ─────────────────────────────────────────────────


async def test_buy_charges_fee(client):
    await _login(client)
    # VOD at 0.72 x 10 = 7.20, fee 1% = 0.07
    r = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"},
    )
    assert r.status_code == 201
    pf = (await client.get("/portfolio")).json()
    assert Decimal(pf["virtual_cash"]) == Decimal("1000.00") - Decimal("7.20") - Decimal("0.07")


async def test_sell_nets_fee(client):
    await _login(client)
    await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"},
    )
    r = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "sell", "shares": "10"},
    )
    assert r.status_code == 201
    # buy: 1000 - 7.20 - 0.07 = 992.73; sell: + (7.20 - 0.07) = 999.86
    pf = (await client.get("/portfolio")).json()
    assert Decimal(pf["virtual_cash"]) == Decimal("999.86")


async def test_trade_response_carries_fee_and_pct(client):
    await _login(client)
    r = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"},
    )
    assert r.status_code == 201
    body = r.json()
    assert Decimal(body["fee"]) == Decimal("0.07")
    assert Decimal(body["commission_pct"]) == Decimal("1.0")


async def test_zero_pct_behaves_like_no_commission(client, db_session):
    await set_trade_commission_pct(db_session, Decimal("0"))
    await _login(client)
    await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "10"},
    )
    r = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "sell", "shares": "10"},
    )
    assert Decimal(r.json()["fee"]) == Decimal("0.00")
    pf = (await client.get("/portfolio")).json()
    assert Decimal(pf["virtual_cash"]) == Decimal("1000.00")


async def test_fee_quantised_to_two_dp(client):
    await _login(client)
    # VOD 0.72 x 3 = 2.16, raw fee 0.0216 -> 0.02
    r = await client.post(
        "/portfolio/trades",
        json={"ticker": "VOD", "exchange": "LSE", "type": "buy", "shares": "3"},
    )
    assert Decimal(r.json()["fee"]) == Decimal("0.02")


async def test_insufficient_funds_when_fee_pushes_over(db_session):
    from datetime import date

    from app.models.simulator import Portfolio
    from app.models.user import User

    user = User(
        email="edgefee@example.com", username="edgefee", password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    # Can afford the value (7.20) but not value + fee (7.27)
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("7.20"), currency_code="GBP")
    db_session.add(portfolio)
    await db_session.flush()

    quote = PriceQuote(ticker="VOD", exchange="LSE", name="Vodafone", price=Decimal("0.72"), currency="GBP")
    with pytest.raises(InsufficientFundsError):
        await execute_trade(db_session, portfolio, quote, "buy", Decimal("10"))


# ── pre-trade visibility ────────────────────────────────────────────


async def test_trade_config_endpoint_returns_pct(client, db_session):
    await _login(client)
    r = await client.get("/market/trade-config")
    assert r.status_code == 200
    assert Decimal(r.json()["commission_pct"]) == Decimal("1.0")

    await set_trade_commission_pct(db_session, Decimal("3"))
    r = await client.get("/market/trade-config")
    assert Decimal(r.json()["commission_pct"]) == Decimal("3")


# ── admin ───────────────────────────────────────────────────────────


async def test_admin_settings_commission_roundtrip(admin_client):
    put = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": [], "trade_commission_pct": "2.5"},
    )
    assert put.status_code == 200
    assert put.json()["trade_commission_pct"] == "2.5"
    get = await admin_client.get("/admin/settings")
    assert get.json()["trade_commission_pct"] == "2.5"


async def test_admin_settings_default_commission(admin_client):
    get = await admin_client.get("/admin/settings")
    assert get.json()["trade_commission_pct"] == "1.0"


@pytest.mark.parametrize("bad", ["11", "-1", "abc"])
async def test_admin_settings_commission_bounds_422(admin_client, bad):
    put = await admin_client.put(
        "/admin/settings",
        json={"alert_emails": [], "trade_commission_pct": bad},
    )
    assert put.status_code == 422
