"""Event-loop protection: blocking price-provider calls must run in a thread.

Router handlers wrap the (synchronous) yfinance-backed provider calls in
``asyncio.to_thread``. If a handler called the provider directly, a slow
Yahoo response would freeze the single uvicorn event loop and stall every
in-flight request. This test proves the loop stays free: a provider whose
``get_quote`` does a *blocking* ``time.sleep(0.3)`` is in flight while a
cheap ``/health`` request still completes almost instantly.
"""

import asyncio
import time

import pytest

from app.main import app
from app.routers.simulator import get_price_provider
from app.services.price_provider import StaticPriceProvider

pytestmark = pytest.mark.asyncio(loop_scope="session")

_SLEEP = 0.3


class BlockingQuoteProvider(StaticPriceProvider):
    """Static provider whose get_quote blocks like a slow yfinance call."""

    def get_quote(self, ticker, exchange):
        time.sleep(_SLEEP)  # deliberately BLOCKING (not asyncio.sleep)
        return super().get_quote(ticker, exchange)


async def _login(client):
    payload = {
        "email": "offload@example.com",
        "username": "offloader",
        "password": "SecurePass123!",
        "dob": "2010-05-10",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }
    await client.post("/auth/register", json=payload)
    await client.post(
        "/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def test_slow_provider_does_not_block_event_loop(client):
    await _login(client)
    app.dependency_overrides[get_price_provider] = lambda: BlockingQuoteProvider()

    start = time.monotonic()

    async def slow_quote():
        r = await client.get("/market/quote/NASDAQ/AAPL")
        return r, time.monotonic() - start

    async def cheap_health():
        # Let the slow request enter its handler first.
        await asyncio.sleep(0.05)
        r = await client.get("/health")
        return r, time.monotonic() - start

    (slow_resp, slow_t), (cheap_resp, cheap_t) = await asyncio.gather(
        slow_quote(), cheap_health()
    )

    assert slow_resp.status_code == 200
    assert cheap_resp.status_code == 200
    # The slow request genuinely took >= the blocking sleep...
    assert slow_t >= _SLEEP
    # ...but the cheap request finished while it was still in flight,
    # proving the blocking provider call ran off the event loop.
    assert cheap_t < _SLEEP * 0.67, (
        f"/health took {cheap_t:.3f}s while a {_SLEEP}s blocking provider call "
        "was in flight — the event loop was blocked"
    )
