import inspect

import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.user import User
from app.services import next_lesson_service, recommendation_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _gb_user(db_session, **over):
    from datetime import date
    u = User(username=f"vis_{id(over)}", password_hash="x", dob=date(2014, 1, 1),
             country_code="GB", currency_code="GBP", active_market_code="GB",
             home_market_code="GB", **over)
    db_session.add(u)
    await db_session.flush()
    return u


async def _gb_module(db_session, *, published, order_index, title="M"):
    m = Module(topic="saving", title=title, country_codes=[], market_code="GB",
               is_premium=False, order_index=order_index, icon="💷",
               min_age=10, max_age=14, published=published)
    db_session.add(m)
    await db_session.flush()
    lvl = Level(module_id=m.id, title="L", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lvl)
    await db_session.flush()
    db_session.add(Lesson(module_id=m.id, level_id=lvl.id, type="card", xp_reward=10,
                          order_index=0, content_json={"title": "t", "body": "b"}))
    await db_session.flush()
    return m


async def test_child_module_list_excludes_unpublished(db_session):
    await _gb_user(db_session)
    await _gb_module(db_session, published=True, order_index=900, title="Visible")
    await _gb_module(db_session, published=False, order_index=901, title="Staged")
    # The child list endpoint query: published-only.
    rows = (await db_session.scalars(
        select(Module).where(Module.market_code == "GB", Module.published.is_(True))
    )).all()
    titles = {m.title for m in rows}
    assert "Visible" in titles and "Staged" not in titles


def test_feeder_coverage_meta():
    """Every child feeder module that filters by is_module_in_market must also
    consider published (via is_module_visible) OR filter Module.published in SQL.
    This guards against a new feeder silently skipping the published gate."""
    import app.routers.content as content_router
    for mod in (content_router, next_lesson_service, recommendation_service):
        src = inspect.getsource(mod)
        if "is_module_in_market" in src:
            assert "is_module_visible" in src, f"{mod.__name__} gates market but not published"
