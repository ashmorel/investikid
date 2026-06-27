import pytest
from app.services import market_snapshot_service
from app.services.price_provider import StaticPriceProvider

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_snapshot_featured_is_region_scoped():
    snap = market_snapshot_service.snapshot(StaticPriceProvider(), "GB")
    assert snap["region"] == "GB"
    assert snap["featured"]                                   # non-empty
    assert all(q["exchange"] == "LSE" for q in snap["featured"])  # GB → LSE only
    assert isinstance(snap["movers"], dict)


def test_snapshot_never_raises_on_provider_error():
    class _Boom(StaticPriceProvider):
        def get_market_movers(self, region): raise RuntimeError("yf down")
    snap = market_snapshot_service.snapshot(_Boom(), "US")
    assert snap["movers"] == {}                               # movers degrade to empty
    assert snap["featured"]                                   # featured still served


async def test_snapshot_endpoint_returns_shape(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="snap@example.com", username="snap")
    r = await client.get("/market/snapshot?region=US")
    assert r.status_code == 200
    body = r.json()
    assert body["region"] == "US" and "featured" in body and "movers" in body


async def test_snapshot_endpoint_rejects_bad_region(client, db_session):
    from tests.test_content import _register_and_login
    await _register_and_login(client, email="snap2@example.com", username="snap2")
    assert (await client.get("/market/snapshot?region=MARS")).status_code == 422
