import pytest

from app.models.market_brief import MarketBrief

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_market_brief_roundtrip(db_session):
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="draft"))
    await db_session.flush()
    db_session.expire_all()

    fetched = await db_session.get(MarketBrief, "US")
    assert fetched is not None
    assert fetched.market_code == "US"
    assert fetched.brief_json == {"currency": "USD"}
    assert fetched.status == "draft"
    assert fetched.model_used == ""
    assert fetched.created_at is not None
    assert fetched.updated_at is not None
