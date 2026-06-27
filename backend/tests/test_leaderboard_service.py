from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.arcade import ArcadeScore
from app.models.content import Lesson, LessonCompletion, Module
from app.models.user import User
from app.services.leaderboard_service import leaderboard
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def _mk_user(client, db_session, email, *, market="GB", country="GB",
                   consent=True, hidden=False, handle=None):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    u.active_market_code = market
    u.country_code = country
    u.leaderboard_consent = consent
    u.leaderboard_hidden = hidden
    u.display_handle = handle or f"Handle{email.split('@')[0]}"
    await db_session.commit()
    return u

async def _ensure_module(db_session):
    """Return (or create) a Module row — one per test transaction is enough."""
    mod = (await db_session.scalars(select(Module).limit(1))).first()
    if mod is None:
        mod = Module(topic="savings", title="Savings", country_codes=[], is_premium=False, order_index=0)
        db_session.add(mod)
        await db_session.flush()
    return mod

async def _add_xp(db_session, user, amount):
    """Create a fresh lesson + completion so each (user, lesson) pair is unique."""
    mod = await _ensure_module(db_session)
    lesson = Lesson(module_id=mod.id, type="card", xp_reward=amount,
                    order_index=0, content_json={"title": "t", "body": "b"})
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.commit()

async def _add_arcade(db_session, user, points, market="GB"):
    db_session.add(ArcadeScore(user_id=user.id, game="quiz_rush", points=points,
                               market_code=market, created_at=datetime.now(UTC)))
    await db_session.commit()

async def test_market_scope_filters_by_market_and_uses_handle(client, db_session):
    me = await _mk_user(client, db_session, "lbm_me@example.com", market="GB")
    other_gb = await _mk_user(client, db_session, "lbm_gb@example.com", market="GB")
    other_us = await _mk_user(client, db_session, "lbm_us@example.com", market="US")
    await _add_xp(db_session, me, 30)
    await _add_xp(db_session, other_gb, 50)
    await _add_xp(db_session, other_us, 99)

    rows = await leaderboard(db_session, viewer=me, scope="market", metric="xp")
    names = [r.name for r in rows]
    assert me.display_handle in names and other_gb.display_handle in names
    assert other_us.display_handle not in names         # different market excluded
    assert all(not r.name.startswith("lbm_") for r in rows)  # handle, never username
    assert any(r.is_me for r in rows)

async def test_public_excludes_non_consented_and_hidden(client, db_session):
    me = await _mk_user(client, db_session, "lbv_me@example.com")
    noconsent = await _mk_user(client, db_session, "lbv_nc@example.com", consent=False)
    hidden = await _mk_user(client, db_session, "lbv_h@example.com", hidden=True)
    for u in (me, noconsent, hidden):
        await _add_xp(db_session, u, 40)

    rows = await leaderboard(db_session, viewer=me, scope="global", metric="xp")
    names = {r.name for r in rows}
    assert noconsent.display_handle not in names
    assert hidden.display_handle not in names
    assert me.display_handle in names

async def test_arcade_metric_uses_arcade_points(client, db_session):
    me = await _mk_user(client, db_session, "lba_me@example.com", market="GB")
    await _add_xp(db_session, me, 5)        # xp present but should be ignored
    await _add_arcade(db_session, me, 250, market="GB")
    rows = await leaderboard(db_session, viewer=me, scope="market", metric="arcade")
    mine = next(r for r in rows if r.is_me)
    assert mine.points == 250


async def test_public_board_is_cached_in_production(client, db_session, monkeypatch):
    """In production the public board is cached: a second view serves the cached
    rows (a DB change in between is not reflected until TTL), while per-viewer
    is_me is still applied on top of the cached data — never stored."""
    from app.services import leaderboard_service, price_cache

    # Force the prod-only cache gate on, backed by an in-memory cache stand-in.
    store: dict = {}
    monkeypatch.setattr(leaderboard_service, "_cache_enabled", lambda: True)
    monkeypatch.setattr(price_cache, "get_json", lambda k: store.get(k))
    monkeypatch.setattr(price_cache, "set_json", lambda k, v, ttl: store.__setitem__(k, v))

    a = await _mk_user(client, db_session, "lbc_a@example.com", market="GB", handle="Alpha")
    b = await _mk_user(client, db_session, "lbc_b@example.com", market="GB", handle="Bravo")
    await _add_xp(db_session, a, 50)
    await _add_xp(db_session, b, 30)

    # First view (as A) populates the cache.
    rows_a = await leaderboard(db_session, viewer=a, scope="market", metric="xp")
    assert store, "expected the board to be cached"
    assert [r.name for r in rows_a][:2] == ["Alpha", "Bravo"]
    assert next(r for r in rows_a if r.name == "Alpha").is_me

    # Mutate the DB: a brand-new top scorer that WOULD lead if recomputed.
    c = await _mk_user(client, db_session, "lbc_c@example.com", market="GB", handle="Champ")
    await _add_xp(db_session, c, 999)

    # Second view (as B) must be served from cache: Champ absent, is_me now Bravo.
    rows_b = await leaderboard(db_session, viewer=b, scope="market", metric="xp")
    names_b = [r.name for r in rows_b]
    assert "Champ" not in names_b, "cache miss — board was recomputed"
    assert next(r for r in rows_b if r.name == "Bravo").is_me
    assert not any(r.is_me and r.name == "Alpha" for r in rows_b)
