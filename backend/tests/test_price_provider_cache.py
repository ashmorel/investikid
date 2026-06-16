import math
from decimal import Decimal

import pandas as pd

import app.services.price_cache as pc
import app.services.price_provider as ppmod
from app.services.price_provider import LivePriceProvider, PriceQuote


class _FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def setex(self, key, ttl, value):
        self.store[key] = value


def setup_function():
    pc.reset()


def test_search_hit_skips_yahoo(monkeypatch):
    monkeypatch.setattr(pc, "_make_client", lambda: _FakeRedis())
    provider = LivePriceProvider()

    def fake_search(q):
        raise AssertionError("yf.Search should not be called on cache hit")

    pc.set_json(
        "mkt:search:nvda",
        [{"ticker": "NVDA", "exchange": "NASDAQ", "name": "NVIDIA Corp.", "price": "525.40", "currency": "USD"}],
        120,
    )
    monkeypatch.setattr(ppmod.yf, "Search", fake_search)

    out = provider.search("NVDA")
    assert len(out) == 1
    assert isinstance(out[0], PriceQuote)
    assert out[0].ticker == "NVDA"
    assert out[0].price == Decimal("525.40")


def test_search_miss_writes_cache(monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(pc, "_make_client", lambda: fake)
    provider = LivePriceProvider()

    class _EmptySearch:
        quotes = []
    monkeypatch.setattr(ppmod.yf, "Search", lambda q: _EmptySearch())
    monkeypatch.setattr(
        provider, "get_quote",
        lambda t, e: PriceQuote(ticker=t.upper(), exchange=e, name="X", price=Decimal("1"), currency="USD"),
    )

    out = provider.search("AAPL")
    assert fake.store.get("mkt:search:aapl") is not None
    assert isinstance(out, list)


def test_search_fallback_when_redis_disabled(monkeypatch):
    def boom():
        raise RuntimeError("no redis")
    monkeypatch.setattr(pc, "_make_client", boom)
    provider = LivePriceProvider()

    class _EmptySearch:
        quotes = []
    monkeypatch.setattr(ppmod.yf, "Search", lambda q: _EmptySearch())
    monkeypatch.setattr(
        provider, "get_quote",
        lambda t, e: PriceQuote(ticker=t.upper(), exchange=e, name="X", price=Decimal("1"), currency="USD"),
    )
    out = provider.search("AAPL")
    assert isinstance(out, list)


def test_get_history_skips_nan_rows(monkeypatch):
    """yfinance can return rows with NaN OHLCV; these must be dropped, not
    serialized as null (which crashed the stock page) or passed to int() (500)."""
    monkeypatch.setattr(pc, "_make_client", lambda: _FakeRedis())
    provider = LivePriceProvider()

    index = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
    df = pd.DataFrame(
        {
            "Open": [100.0, float("nan"), 102.0],
            "High": [101.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 102.5, float("nan")],
            "Volume": [1000, 2000, float("nan")],
        },
        index=index,
    )

    class _FakeTicker:
        def __init__(self, symbol):
            self._symbol = symbol
            self.fast_info = {"currency": "USD"}

        def history(self, period="1mo"):
            return df

    monkeypatch.setattr(ppmod.yf, "Ticker", _FakeTicker)

    points = provider.get_history("ARM", "NASDAQ", "1mo")

    # Only the first row is fully finite; rows 2 (NaN open) and 3 (NaN close/volume) are dropped.
    assert len(points) == 1
    assert points[0].date == "2024-01-01"
    assert all(math.isfinite(p.close) for p in points)
    assert all(math.isfinite(p.open) for p in points)
