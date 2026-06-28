"""Tests for TwelveDataProvider (prototype behind price_provider flag).

All HTTP calls are mocked — the live Twelve Data API is never hit.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.price_provider import (
    _FEATURED,
    LivePriceProvider,
    MarketMover,
    PricePoint,
    PriceQuote,
    TickerNotAvailableError,
)
from app.services.twelvedata_provider import TwelveDataError, TwelveDataProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_provider(api_key: str = "test-key") -> TwelveDataProvider:
    return TwelveDataProvider(api_key=api_key)


# ---------------------------------------------------------------------------
# get_quote — USD ticker (AAPL/NASDAQ)
# ---------------------------------------------------------------------------

def test_get_quote_maps_close_currency_name(monkeypatch):
    p = make_provider()
    monkeypatch.setattr(
        p, "_get",
        lambda endpoint, params: {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "currency": "USD",
            "close": "195.50",
            "percent_change": "0.5",
        },
    )
    q = p.get_quote("AAPL", "NASDAQ")
    assert q.ticker == "AAPL"
    assert q.exchange == "NASDAQ"
    assert q.name == "Apple Inc."
    assert q.price == Decimal("195.50")
    assert q.currency == "USD"


def test_get_quote_pence_conversion(monkeypatch):
    """LSE tickers priced in GBp must be divided by 100 → GBP."""
    p = make_provider()
    monkeypatch.setattr(
        p, "_get",
        lambda endpoint, params: {
            "symbol": "VOD",
            "name": "Vodafone Group",
            "exchange": "LSE",
            "currency": "GBp",
            "close": "72.50",
            "percent_change": "-0.3",
        },
    )
    q = p.get_quote("VOD", "LSE")
    assert q.currency == "GBP"
    # 72.50 pence → £0.73 (rounded to 2dp)
    assert q.price == Decimal("0.73")


def test_get_quote_featured_fallback_on_error(monkeypatch):
    """If the API errors and the ticker is in _FEATURED, use the fallback."""
    p = make_provider()

    def _error(endpoint, params):
        raise TwelveDataError("API limit reached")

    monkeypatch.setattr(p, "_get", _error)
    q = p.get_quote("AAPL", "NASDAQ")
    featured = _FEATURED[("AAPL", "NASDAQ")]
    assert q.price == featured[1]
    assert q.name == featured[0]
    assert q.currency == featured[2]


def test_get_quote_unknown_ticker_raises(monkeypatch):
    """Unknown ticker with API error should raise TickerNotAvailableError."""
    p = make_provider()

    def _error(endpoint, params):
        raise TwelveDataError("symbol not found")

    monkeypatch.setattr(p, "_get", _error)
    with pytest.raises(TickerNotAvailableError):
        p.get_quote("XYZNOTREAL", "NASDAQ")


def test_get_quote_reads_l2_cache(monkeypatch):
    """L2 (Redis) hit should skip the live API call entirely."""
    p = make_provider()
    monkeypatch.setattr(
        "app.services.twelvedata_provider.price_cache.get_json",
        lambda key: {
            "ticker": "MSFT", "exchange": "NASDAQ", "name": "Microsoft Corp.",
            "price": "400.00", "currency": "USD",
        },
    )
    api_called = []
    monkeypatch.setattr(p, "_get", lambda *a, **kw: api_called.append(1) or {})
    q = p.get_quote("MSFT", "NASDAQ")
    assert q.price == Decimal("400.00")
    assert not api_called, "Live API should not be called when L2 hit"


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

def test_get_history_builds_oldest_first_price_points(monkeypatch):
    p = make_provider()
    # Twelve Data returns newest-first; provider must reverse.
    td_response = {
        "meta": {"currency": "USD"},
        "values": [
            {"datetime": "2024-01-05", "open": "190", "high": "192", "low": "188", "close": "191", "volume": "5000"},
            {"datetime": "2024-01-04", "open": "188", "high": "191", "low": "187", "close": "190", "volume": "4500"},
            {"datetime": "2024-01-03", "open": "185", "high": "189", "low": "184", "close": "188", "volume": "6000"},
        ],
    }
    monkeypatch.setattr(p, "_get", lambda endpoint, params: td_response)
    points = p.get_history("AAPL", "NASDAQ", period="1mo")
    assert len(points) == 3
    # Oldest date must come first
    assert points[0].date == "2024-01-03"
    assert points[-1].date == "2024-01-05"
    assert isinstance(points[0], PricePoint)
    assert points[0].open == 185.0
    assert points[0].volume == 6000


def test_get_history_pence_conversion_for_lse(monkeypatch):
    """LSE history values in GBp should be divided by 100 (via featured lookup)."""
    p = make_provider()
    td_response = {
        "meta": {"currency": "GBp"},
        "values": [
            {"datetime": "2024-01-03", "open": "7200", "high": "7250", "low": "7150", "close": "7220", "volume": "1000"},
        ],
    }
    monkeypatch.setattr(p, "_get", lambda endpoint, params: td_response)
    # BP is in _FEATURED with currency GBP
    points = p.get_history("BP", "LSE", period="1mo")
    assert len(points) == 1
    assert points[0].close == 72.20


def test_get_history_returns_empty_on_failure(monkeypatch):
    p = make_provider()
    monkeypatch.setattr(p, "_get", lambda *a, **kw: (_ for _ in ()).throw(Exception("boom")))
    result = p.get_history("AAPL", "NASDAQ")
    assert result == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_search_maps_symbol_search_results(monkeypatch):
    p = make_provider()
    td_response = {
        "data": [
            {
                "symbol": "TSLA",
                "instrument_name": "Tesla Inc.",
                "exchange": "NASDAQ",
                "instrument_type": "Common Stock",
                "currency": "USD",
            },
            {
                "symbol": "TSLA-USD",
                "instrument_name": "Tesla Token",
                "exchange": "CRYPTO",
                "instrument_type": "Digital Currency",  # should be filtered out
                "currency": "USD",
            },
        ]
    }
    monkeypatch.setattr(p, "_get", lambda endpoint, params: td_response)
    results = p.search("TSLA")
    assert len(results) == 1
    assert results[0].ticker == "TSLA"
    assert results[0].exchange == "NASDAQ"
    assert results[0].name == "Tesla Inc."


def test_search_empty_query_returns_featured(monkeypatch):
    """Empty query must return featured quotes (from L2 / _FEATURED fallback)."""
    p = make_provider()
    # Make get_quote return a quote from _FEATURED
    def _mock_get_quote(ticker, exchange):
        f = _FEATURED.get((ticker.upper(), exchange.upper()))
        if not f:
            raise TickerNotAvailableError
        return PriceQuote(ticker=ticker, exchange=exchange, name=f[0], price=f[1], currency=f[2])

    monkeypatch.setattr(p, "get_quote", _mock_get_quote)
    results = p.search("")
    assert len(results) == len(_FEATURED)


def test_search_returns_featured_on_error(monkeypatch):
    """API error during search falls back to matching featured tickers."""
    p = make_provider()

    def _error(endpoint, params):
        raise TwelveDataError("network error")

    monkeypatch.setattr(p, "_get", _error)
    results = p.search("AAPL")
    tickers = [r.ticker for r in results]
    assert "AAPL" in tickers


# ---------------------------------------------------------------------------
# get_market_movers
# ---------------------------------------------------------------------------

def test_get_market_movers_returns_nested_structure(monkeypatch):
    """Movers should return {exchange: {winners: [...], losers: [...]}}."""
    p = make_provider()

    def _mock_get(endpoint, params):
        # Simulate alternating winners/losers based on ticker
        if params.get("symbol") in ("AAPL", "MSFT"):
            return {
                "close": "200.00",
                "currency": "USD",
                "percent_change": "2.5",
            }
        if params.get("symbol") in ("GOOGL", "AMZN"):
            return {
                "close": "150.00",
                "currency": "USD",
                "percent_change": "-1.5",
            }
        return {"close": "100.00", "currency": "USD", "percent_change": "0.0"}

    monkeypatch.setattr(p, "_get", _mock_get)
    # Also stub cache miss
    monkeypatch.setattr(
        "app.services.twelvedata_provider.price_cache.get_json",
        lambda key: None,
    )
    monkeypatch.setattr(
        "app.services.twelvedata_provider.price_cache.set_json",
        lambda *a, **kw: None,
    )
    result = p.get_market_movers("US")
    # Should have at least the NASDAQ key (US region has NASDAQ + NYSE)
    assert isinstance(result, dict)
    for exch, sides in result.items():
        assert "winners" in sides
        assert "losers" in sides
        assert all(isinstance(m, MarketMover) for m in sides["winners"])
        assert all(isinstance(m, MarketMover) for m in sides["losers"])
        # Winners have positive change; losers have negative
        assert all(m.change_percent > 0 for m in sides["winners"])
        assert all(m.change_percent < 0 for m in sides["losers"])


def test_get_market_movers_uses_l2_cache(monkeypatch):
    """If L2 returns movers, the API must not be called."""
    from app.services.price_provider import _movers_to_dict

    p = make_provider()
    cached_mover = MarketMover(
        ticker="AAPL", exchange="NASDAQ", name="Apple Inc.",
        price=Decimal("190.00"), currency="USD", change_percent=1.5,
    )
    cached = _movers_to_dict({"NASDAQ": {"winners": [cached_mover], "losers": []}})
    monkeypatch.setattr(
        "app.services.twelvedata_provider.price_cache.get_json",
        lambda key: cached if "movers" in key else None,
    )
    api_called = []
    monkeypatch.setattr(p, "_get", lambda *a, **kw: api_called.append(1) or {})
    result = p.get_market_movers("US")
    assert not api_called
    assert "NASDAQ" in result


# ---------------------------------------------------------------------------
# get_news
# ---------------------------------------------------------------------------

def test_get_news_returns_empty_list():
    """Twelve Data has no news API; get_news must always return []."""
    p = make_provider()
    result = p.get_news([("AAPL", "NASDAQ"), ("TSLA", "NASDAQ")])
    assert result == []


# ---------------------------------------------------------------------------
# is_free_tier
# ---------------------------------------------------------------------------

def test_is_free_tier_always_true():
    """Mirror LivePriceProvider: all tickers are free tier."""
    p = make_provider()
    assert p.is_free_tier("AAPL", "NASDAQ") is True
    assert p.is_free_tier("0700", "HKEX") is True
    assert p.is_free_tier("XYZUNKNOWN", "NYSE") is True


# ---------------------------------------------------------------------------
# warm_region
# ---------------------------------------------------------------------------

def test_warm_region_returns_expected_dict(monkeypatch):
    p = make_provider()

    def _mock_fetch_quote(ticker, exchange, *, cache_ttl):
        f = _FEATURED.get((ticker.upper(), exchange.upper()))
        if not f:
            raise TickerNotAvailableError
        return PriceQuote(ticker=ticker, exchange=exchange, name=f[0], price=f[1], currency=f[2])

    def _mock_fetch_movers(region, *, cache_ttl):
        return {}

    monkeypatch.setattr(p, "_fetch_quote", _mock_fetch_quote)
    monkeypatch.setattr(p, "_fetch_market_movers", _mock_fetch_movers)
    result = p.warm_region("US")
    assert result["region"] == "US"
    assert isinstance(result["featured"], int)
    assert result["featured"] > 0
    assert result["movers"] is True


# ---------------------------------------------------------------------------
# Factory — default provider and flag-based selection
# ---------------------------------------------------------------------------

def test_factory_returns_live_provider_by_default():
    """With no env vars set, the factory must return LivePriceProvider."""
    from app.routers.simulator import _make_price_provider

    with patch("app.routers.simulator.settings") as mock_settings:
        mock_settings.price_provider = "yfinance"
        mock_settings.twelvedata_api_key = ""
        provider = _make_price_provider()
    assert isinstance(provider, LivePriceProvider)


def test_factory_returns_twelvedata_when_flag_and_key_set():
    """With price_provider='twelvedata' and a key, the factory returns TwelveDataProvider."""
    from app.routers.simulator import _make_price_provider

    with patch("app.routers.simulator.settings") as mock_settings:
        mock_settings.price_provider = "twelvedata"
        mock_settings.twelvedata_api_key = "td-live-key"
        provider = _make_price_provider()
    assert isinstance(provider, TwelveDataProvider)


def test_factory_stays_live_when_flag_set_but_no_key():
    """With price_provider='twelvedata' but no key, must fall back to LivePriceProvider."""
    from app.routers.simulator import _make_price_provider

    with patch("app.routers.simulator.settings") as mock_settings:
        mock_settings.price_provider = "twelvedata"
        mock_settings.twelvedata_api_key = ""
        provider = _make_price_provider()
    assert isinstance(provider, LivePriceProvider)


def test_factory_stays_live_with_unknown_provider_name():
    """Unknown provider name must fall back to LivePriceProvider (safe default)."""
    from app.routers.simulator import _make_price_provider

    with patch("app.routers.simulator.settings") as mock_settings:
        mock_settings.price_provider = "polygon"
        mock_settings.twelvedata_api_key = ""
        provider = _make_price_provider()
    assert isinstance(provider, LivePriceProvider)
