from decimal import Decimal

import pytest

from app.services.price_provider import (
    PriceQuote,
    StaticPriceProvider,
    TickerNotAvailableError,
)


def test_static_provider_returns_quote_for_known_ticker():
    p = StaticPriceProvider()
    q = p.get_quote("AAPL", "NASDAQ")
    assert isinstance(q, PriceQuote)
    assert q.ticker == "AAPL"
    assert isinstance(q.price, Decimal)
    assert q.price > 0


def test_static_provider_rejects_unknown_ticker():
    p = StaticPriceProvider()
    with pytest.raises(TickerNotAvailableError):
        p.get_quote("NOTAREALSTOCK", "NASDAQ")


def test_search_by_prefix_returns_matches():
    p = StaticPriceProvider()
    results = p.search("APP")
    tickers = [r.ticker for r in results]
    assert "AAPL" in tickers


def test_search_empty_query_returns_empty():
    p = StaticPriceProvider()
    assert p.search("") == []


def test_is_free_tier_allows_known_ticker():
    p = StaticPriceProvider()
    assert p.is_free_tier("AAPL", "NASDAQ") is True
    assert p.is_free_tier("NOTREAL", "NASDAQ") is False
