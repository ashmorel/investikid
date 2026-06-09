from decimal import Decimal

import pytest

from app.services.price_provider import _FEATURED, REGION_EXCHANGES, LivePriceProvider

REGISTER_URL = "/auth/register"
LOGIN_URL = "/auth/login"
_USER_BASE = {
    "password": "SecurePass123!",
    "dob": "2010-05-10",
    "country_code": "GB",
    "currency_code": "GBP",
    "parent_email": "parent@example.com",
}


async def _login(client, email="movers@example.com", username="movers"):
    payload = {**_USER_BASE, "email": email, "username": username}
    await client.post(REGISTER_URL, json=payload)
    await client.post(LOGIN_URL, json={"email": email, "password": "SecurePass123!"})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


class _FakeMoversProvider:
    def get_market_movers(self, region):
        if region == "GB":
            return {"LSE": {"winners": [], "losers": []}}
        return {}


@pytest.mark.asyncio(loop_scope="session")
async def test_movers_endpoint_region_param(client):
    from app.main import app
    from app.routers.simulator import get_price_provider

    await _login(client)
    app.dependency_overrides[get_price_provider] = lambda: _FakeMoversProvider()
    try:
        r = await client.get("/market/movers?region=GB")
        assert r.status_code == 200
        assert set(r.json().keys()) == {"LSE"}

        r_default = await client.get("/market/movers")  # defaults to US
        assert r_default.status_code == 200
        assert r_default.json() == {}

        r_bad = await client.get("/market/movers?region=ZZ")
        assert r_bad.status_code == 422
    finally:
        app.dependency_overrides.pop(get_price_provider, None)


def _provider(changes: dict[str, float]) -> LivePriceProvider:
    """LivePriceProvider with _quote_change stubbed so no network is hit.
    `changes` maps ticker -> change_percent."""
    p = LivePriceProvider()

    def fake(ticker, exchange, fallback_price, currency):
        return Decimal("100.00"), currency, changes.get(ticker, 0.0)

    p._quote_change = fake  # type: ignore[assignment]
    return p


def test_region_exchanges_map():
    assert REGION_EXCHANGES == {"US": ["NASDAQ", "NYSE"], "GB": ["LSE"], "HK": ["HKEX"]}


def test_featured_expanded():
    for key in [("DIS", "NYSE"), ("KO", "NYSE"), ("NKE", "NYSE"), ("MCD", "NYSE"),
                ("BARC", "LSE"), ("GSK", "LSE"), ("RR", "LSE"),
                ("9988", "HKEX"), ("1810", "HKEX"), ("1211", "HKEX"), ("0992", "HKEX")]:
        assert key in _FEATURED


def test_movers_gb_only_lse_sorted():
    p = _provider({"VOD": 3.0, "BP": -2.0, "HSBA": 1.0, "TSCO": -0.5})
    res = p.get_market_movers("GB")
    assert set(res.keys()) == {"LSE"}
    winners = [m.ticker for m in res["LSE"]["winners"]]
    losers = [m.ticker for m in res["LSE"]["losers"]]
    assert winners[0] == "VOD"            # biggest gainer first
    assert losers[0] == "BP"              # biggest loser first
    assert "VOD" not in losers and "BP" not in winners


def test_movers_us_covers_both_exchanges():
    p = _provider({"AAPL": 5.0, "DIS": -3.0})
    res = p.get_market_movers("US")
    assert "NASDAQ" in res and "NYSE" in res
    assert [m.ticker for m in res["NASDAQ"]["winners"]][0] == "AAPL"
    assert [m.ticker for m in res["NYSE"]["losers"]][0] == "DIS"


def test_movers_hk_only_hkex():
    p = _provider({"0700": 2.0})
    res = p.get_market_movers("HK")
    assert set(res.keys()) == {"HKEX"}


def test_movers_flat_day_is_empty():
    p = _provider({})  # all 0.0 -> in neither winners nor losers
    assert p.get_market_movers("GB") == {}
