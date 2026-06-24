# backend/tests/test_collectables_service.py
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import User, UserProgress
from app.services.collectables_service import grant_eligible
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(client, db_session, email, *, streak=0):
    await _register_and_login(client, email=email, username=email.split("@")[0])
    u = await db_session.scalar(select(User).where(User.email == email))
    p = await db_session.get(UserProgress, u.id) or UserProgress(user_id=u.id)
    p.streak_count = streak
    db_session.add(p)
    await db_session.commit()
    return u, p


def _drop(slug, utype, thr, *, open_days_ago=1, closes_in_days=7):
    now = datetime.now(UTC)
    return CosmeticItem(
        slug=slug,
        name=slug,
        emoji="👑",
        type="accessory",
        coin_cost=0,
        is_premium=False,
        rarity="legendary",
        unlock_type=utype,
        unlock_threshold=thr,
        available_from=now - timedelta(days=open_days_ago),
        available_until=now + timedelta(days=closes_in_days),
    )


async def test_streak_drop_granted_when_met_and_idempotent(client, db_session):
    u, p = await _user(client, db_session, "col_s@example.com", streak=7)
    drop = _drop("_d_streak", "streak_days", 7)
    db_session.add(drop)
    await db_session.commit()
    granted = await grant_eligible(db_session, p)
    assert "_d_streak" in granted
    owned = await db_session.scalar(
        select(UserCosmetic).where(
            UserCosmetic.user_id == u.id, UserCosmetic.item_id == drop.id
        )
    )
    assert owned is not None and owned.equipped is False
    # idempotent
    assert await grant_eligible(db_session, p) == []


async def test_streak_drop_not_granted_when_below_threshold(client, db_session):
    _, p = await _user(client, db_session, "col_lo@example.com", streak=3)
    db_session.add(_drop("_d_streak2", "streak_days", 7))
    await db_session.commit()
    assert "_d_streak2" not in await grant_eligible(db_session, p)


async def test_closed_window_never_granted(client, db_session):
    _, p = await _user(client, db_session, "col_closed@example.com", streak=99)
    db_session.add(_drop("_d_closed", "streak_days", 1, open_days_ago=30, closes_in_days=-1))
    await db_session.commit()
    assert "_d_closed" not in await grant_eligible(db_session, p)
