"""Performance behaviours: parallel fan-outs, stale-while-revalidate, startup warm."""

import threading
import time
from decimal import Decimal

from app.main import warm_price_cache
from app.services.price_provider import (
    _CACHE_TTL,
    LivePriceProvider,
    PriceQuote,
)


def _wait_for(predicate, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _quote(price: str = "100.00") -> PriceQuote:
    return PriceQuote(
        ticker="AAPL", exchange="NASDAQ", name="Apple Inc.",
        price=Decimal(price), currency="USD",
    )


# --- parallel fan-out -------------------------------------------------------

def test_market_movers_fetches_quotes_in_parallel():
    p = LivePriceProvider()
    calls: list[str] = []

    def slow_change(ticker, exchange, fallback_price, currency):
        calls.append(ticker)
        time.sleep(0.1)
        return Decimal("100.00"), currency, 1.0

    p._quote_change = slow_change  # type: ignore[assignment]

    start = time.monotonic()
    result = p.get_market_movers("GB")  # 7 LSE featured tickers
    elapsed = time.monotonic() - start

    assert len(calls) >= 6
    # Serial would take >= 0.6s; bounded pool of 8 runs them concurrently.
    assert elapsed < 0.35, f"movers fan-out took {elapsed:.2f}s (looks serial)"
    assert "LSE" in result and result["LSE"]["winners"]


# --- stale-while-revalidate -------------------------------------------------

def test_get_quote_serves_stale_and_refreshes_in_background():
    p = LivePriceProvider()
    key = ("AAPL", "NASDAQ")
    stale = _quote("100.00")
    p._cache[key] = (stale, time.monotonic() - _CACHE_TTL - 1)

    fetch_count = 0

    def fake_fetch(ticker, exchange):
        nonlocal fetch_count
        fetch_count += 1
        fresh = _quote("123.45")
        p._cache[(ticker, exchange)] = (fresh, time.monotonic())
        return fresh

    p._fetch_quote = fake_fetch  # type: ignore[assignment]

    start = time.monotonic()
    result = p.get_quote("AAPL", "NASDAQ")
    elapsed = time.monotonic() - start

    assert result.price == Decimal("100.00")  # old value, instantly
    assert elapsed < 0.05
    assert _wait_for(lambda: p._cache[key][0].price == Decimal("123.45"))
    assert fetch_count == 1
    # Once refreshed, the fresh value is served with no further fetches.
    assert p.get_quote("AAPL", "NASDAQ").price == Decimal("123.45")
    assert fetch_count == 1


def test_concurrent_stale_quote_calls_trigger_single_refresh():
    p = LivePriceProvider()
    key = ("AAPL", "NASDAQ")
    p._cache[key] = (_quote("100.00"), time.monotonic() - _CACHE_TTL - 1)

    fetch_count = 0
    lock = threading.Lock()

    def slow_fetch(ticker, exchange):
        nonlocal fetch_count
        with lock:
            fetch_count += 1
        time.sleep(0.1)
        fresh = _quote("123.45")
        p._cache[(ticker, exchange)] = (fresh, time.monotonic())
        return fresh

    p._fetch_quote = slow_fetch  # type: ignore[assignment]

    results: list[PriceQuote] = []
    threads = [
        threading.Thread(target=lambda: results.append(p.get_quote("AAPL", "NASDAQ")))
        for _ in range(5)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(r.price == Decimal("100.00") for r in results)  # all served stale
    assert _wait_for(lambda: p._cache[key][0].price == Decimal("123.45"))
    assert fetch_count == 1  # no thundering herd


def test_market_movers_serves_stale_and_refreshes():
    p = LivePriceProvider()
    stale_result = {"LSE": {"winners": [], "losers": []}}
    p._history_cache["_movers:GB"] = (stale_result, time.monotonic() - _CACHE_TTL - 1)

    fetch_count = 0

    def fake_fetch(region):
        nonlocal fetch_count
        fetch_count += 1
        fresh = {"LSE": {"winners": ["x"], "losers": []}}
        p._history_cache[f"_movers:{region}"] = (fresh, time.monotonic())
        return fresh

    p._fetch_market_movers = fake_fetch  # type: ignore[assignment]

    assert p.get_market_movers("GB") == stale_result  # stale, instantly
    assert _wait_for(lambda: fetch_count == 1)
    assert _wait_for(
        lambda: p._history_cache["_movers:GB"][0]["LSE"]["winners"] == ["x"]
    )


def test_failed_refresh_clears_inflight_so_next_stale_call_retries():
    p = LivePriceProvider()
    key = ("AAPL", "NASDAQ")
    p._cache[key] = (_quote("100.00"), time.monotonic() - _CACHE_TTL - 1)

    def boom(ticker, exchange):
        raise RuntimeError("yahoo down")

    p._fetch_quote = boom  # type: ignore[assignment]

    assert p.get_quote("AAPL", "NASDAQ").price == Decimal("100.00")
    assert _wait_for(lambda: not p._refreshing)  # in-flight key released


def test_fresh_miss_still_fetches_synchronously():
    p = LivePriceProvider()

    def fake_fetch(ticker, exchange):
        fresh = _quote("55.00")
        p._cache[(ticker, exchange)] = (fresh, time.monotonic())
        return fresh

    p._fetch_quote = fake_fetch  # type: ignore[assignment]
    assert p.get_quote("AAPL", "NASDAQ").price == Decimal("55.00")


# --- startup warm -----------------------------------------------------------

def test_warm_price_cache_survives_provider_errors():
    class BrokenProvider:
        def get_market_movers(self, region):
            raise RuntimeError("yahoo down")

    warm_price_cache(provider=BrokenProvider())  # must not raise


def test_warm_price_cache_primes_all_regions():
    regions: list[str] = []

    class SpyProvider:
        def get_market_movers(self, region):
            regions.append(region)
            return {}

    warm_price_cache(provider=SpyProvider())
    assert regions == ["US", "GB", "HK"]
