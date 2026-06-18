import pytest
from sqlalchemy import select

from app.seed.markets import MARKETS, seed_markets
from app.models.market import Market

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_market_catalog_has_ten_iso_coded_markets():
    codes = {m["code"] for m in MARKETS}
    assert codes == {"GB", "US", "AU", "CA", "IE", "ES", "FR", "DE", "HK", "SG"}
    by_code = {m["code"]: m for m in MARKETS}
    assert by_code["GB"]["currency_code"] == "GBP"
    assert by_code["GB"]["default_language"] == "en"
    assert by_code["GB"]["has_content"] is True
    assert by_code["ES"]["default_language"] == "es"
    assert by_code["HK"]["currency_code"] == "HKD"
    assert {m["code"] for m in MARKETS if m["has_content"]} == {"GB"}


async def test_seed_markets_is_idempotent(db_session):
    await seed_markets(db_session)
    await seed_markets(db_session)
    rows = (await db_session.scalars(select(Market))).all()
    assert len(rows) == 10
    gb = await db_session.get(Market, "GB")
    assert gb.name == "United Kingdom"
    assert gb.currency_code == "GBP"
    assert gb.has_content is True
