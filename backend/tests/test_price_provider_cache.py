from decimal import Decimal

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
