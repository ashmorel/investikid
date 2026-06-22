import datetime as dt

import pytest
from sqlalchemy import select

from app.models.content import Module
from app.models.market import Market
from app.seed.markets import MARKETS, reconcile_market_content, seed_markets

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


async def test_seed_markets_does_not_clobber_has_content_on_existing_rows(db_session):
    """A market published after the initial seed must keep has_content across
    re-seeds — otherwise every redeploy silently un-publishes it."""
    await seed_markets(db_session)
    us = await db_session.get(Market, "US")
    us.has_content = True  # simulate US content having been published
    await db_session.flush()

    await seed_markets(db_session)  # a later redeploy re-runs the seed

    us = await db_session.get(Market, "US")
    assert us.has_content is True  # not reset to the seed default (False)


async def test_reconcile_promotes_markets_with_published_modules(db_session):
    await seed_markets(db_session)
    db_session.add(
        Module(topic="saving", title="US Saving", order_index=0, market_code="US", published=True)
    )
    # An archived or unpublished module must NOT count as content.
    db_session.add(
        Module(topic="saving", title="HK Draft", order_index=0, market_code="HK", published=False)
    )
    db_session.add(
        Module(
            topic="saving", title="HK Retired", order_index=1, market_code="HK", published=True,
            archived_at=dt.datetime.now(dt.UTC),
        )
    )
    await db_session.flush()

    await reconcile_market_content(db_session)

    assert (await db_session.get(Market, "US")).has_content is True   # live module → promoted
    assert (await db_session.get(Market, "HK")).has_content is False  # only draft/archived → not
    assert (await db_session.get(Market, "AU")).has_content is False  # no modules → unchanged
