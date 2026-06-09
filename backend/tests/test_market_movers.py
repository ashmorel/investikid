from decimal import Decimal

from app.services.price_provider import _FEATURED, REGION_EXCHANGES, LivePriceProvider


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
