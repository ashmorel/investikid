"""Unit tests for the prod-only daily LLM cache helper (#9)."""
from app.services import llm_cache, price_cache


def test_noop_outside_production(monkeypatch):
    """Outside production the cache must be fully inert: get returns None and
    put never touches Redis (so dev/test always generate live)."""
    monkeypatch.setattr(llm_cache, "_enabled", lambda: False)
    calls = []
    monkeypatch.setattr(price_cache, "get_json", lambda k: calls.append(("get", k)))
    monkeypatch.setattr(price_cache, "set_json", lambda k, v, t: calls.append(("set", k)))

    assert llm_cache.get("home_greeting", ["a", "b"]) is None
    llm_cache.put("home_greeting", ["a", "b"], "hi", 60)
    assert calls == []  # never reached the Redis layer


def test_round_trip_in_production(monkeypatch):
    """In production put stores and get retrieves the same value."""
    store: dict = {}
    monkeypatch.setattr(llm_cache, "_enabled", lambda: True)
    monkeypatch.setattr(price_cache, "get_json", lambda k: store.get(k))
    monkeypatch.setattr(price_cache, "set_json", lambda k, v, ttl: store.__setitem__(k, v))

    parts = ["Alice", "default", "Saving", "3", "1", "explorer", "en"]
    assert llm_cache.get("home_greeting", parts) is None      # cold
    llm_cache.put("home_greeting", parts, "Hi Alice!", 60)
    assert llm_cache.get("home_greeting", parts) == "Hi Alice!"

    # JSON values (the news summary stores a dict) round-trip too.
    llm_cache.put("news_summary", ["AAPL,TSLA", "12", "en"],
                  {"summary": "Stocks moved.", "tickers": ["AAPL"]}, 60)
    got = llm_cache.get("news_summary", ["AAPL,TSLA", "12", "en"])
    assert got == {"summary": "Stocks moved.", "tickers": ["AAPL"]}


def test_key_is_surface_day_and_input_scoped(monkeypatch):
    """Keys are namespaced by surface, include the UTC day, and differ when any
    input part differs (so a progress change yields a fresh entry)."""
    monkeypatch.setattr(llm_cache, "_enabled", lambda: True)

    k1 = llm_cache._key("home_greeting", ["a", "b"])
    k2 = llm_cache._key("home_greeting", ["a", "c"])     # different inputs
    k3 = llm_cache._key("news_summary", ["a", "b"])      # different surface

    from datetime import UTC, datetime
    today = datetime.now(UTC).date().isoformat()
    assert k1.startswith(f"llm:home_greeting:{today}:")
    assert k1 != k2                                       # input-sensitive
    assert k3.startswith("llm:news_summary:")            # surface-namespaced
    assert k1 != k3
