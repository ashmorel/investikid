"""Task 1: leaderboard rows carry the user's equipped avatar."""
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Module
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User
from app.services.leaderboard_service import leaderboard
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk(client, db_session, email, *, market="GB"):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    u.active_market_code = market
    u.country_code = "GB"
    u.leaderboard_consent = True
    u.leaderboard_hidden = False
    u.display_handle = f"H{email.split('@')[0]}"
    await db_session.commit()
    return u


async def _equip(db_session, user, slug, ctype):
    item = await db_session.scalar(select(CosmeticItem).where(CosmeticItem.slug == slug))
    if item is None:
        item = CosmeticItem(slug=slug, name=slug, emoji="🎩", type=ctype, coin_cost=0, is_premium=False)
        db_session.add(item)
        await db_session.flush()
    db_session.add(UserCosmetic(user_id=user.id, item_id=item.id, equipped=True, unlocked_at=datetime.now(UTC)))
    await db_session.commit()


async def _add_xp(db_session, user, amount):
    """Create a fresh module + lesson + completion so each (user, lesson) pair is unique.

    NOTE: Brief's helper omitted required Lesson fields (type, content_json) and
    required Module fields (topic, country_codes, is_premium, order_index). Adapted
    to match the working pattern in test_leaderboard_service.py and the actual models.
    """
    mod = Module(
        topic="savings",
        title="M",
        country_codes=[],
        is_premium=False,
        order_index=0,
        market_code="GB",
    )
    db_session.add(mod)
    await db_session.flush()
    lesson = Lesson(
        module_id=mod.id,
        type="card",
        xp_reward=amount,
        order_index=0,
        content_json={"title": "t", "body": "b"},
    )
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, completed_at=datetime.now(UTC)))
    await db_session.commit()


async def test_rows_include_equipped_avatar(client, db_session):
    me = await _mk(client, db_session, "av_me@example.com")
    await _equip(db_session, me, "skin_sky", "skin")
    await _equip(db_session, me, "party_hat", "accessory")
    await _equip(db_session, me, "sunglasses", "accessory")
    await _add_xp(db_session, me, 30)

    rows = await leaderboard(db_session, viewer=me, scope="market", metric="xp")
    mine = next(r for r in rows if r.is_me)
    assert mine.avatar.skin == "skin_sky"
    assert set(mine.avatar.accessories) == {"party_hat", "sunglasses"}


async def test_row_with_no_cosmetics_has_empty_avatar(client, db_session):
    me = await _mk(client, db_session, "av_bare@example.com")
    await _add_xp(db_session, me, 10)
    rows = await leaderboard(db_session, viewer=me, scope="global", metric="xp")
    mine = next(r for r in rows if r.is_me)
    assert mine.avatar.skin is None
    assert mine.avatar.accessories == []
