from datetime import date, timedelta

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_streak_config_constants():
    from app.services import streak_config
    assert streak_config.STREAK_MILESTONE == 7
    assert streak_config.STREAK_FREEZE_CAP == 2
    assert streak_config.STREAK_FREEZE_GAP == 2


async def test_user_progress_has_streak_freezes_default_zero(db_session):
    from app.models.user import User, UserProgress

    u = User(
        username="freezekid", password_hash="x",
        dob=date(2014, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(u)
    await db_session.flush()
    db_session.add(UserProgress(user_id=u.id))
    await db_session.flush()

    p = await db_session.scalar(select(UserProgress).where(UserProgress.user_id == u.id))
    assert p.streak_freezes == 0


def test_streak_after_activity_freeze_matrix():
    from app.services.content_service import streak_after_activity

    d = date(2026, 1, 15)
    f = streak_after_activity
    # (last, current, freezes, today) -> (streak, last, freezes)
    assert f(None, 0, 0, d) == (1, d, 0)                    # first ever
    assert f(d, 5, 1, d) == (5, d, 1)                       # same day, no change
    assert f(d - timedelta(days=1), 5, 0, d) == (6, d, 0)   # consecutive
    assert f(d - timedelta(days=1), 6, 0, d) == (7, d, 1)   # milestone grants a freeze
    assert f(d - timedelta(days=1), 13, 1, d) == (14, d, 2) # 2nd milestone -> cap edge
    assert f(d - timedelta(days=1), 6, 2, d) == (7, d, 2)   # milestone but already at cap
    assert f(d - timedelta(days=2), 5, 1, d) == (6, d, 0)   # 1 missed day, freeze absorbs
    assert f(d - timedelta(days=2), 6, 1, d) == (7, d, 1)   # freeze absorb + milestone (net 0)
    assert f(d - timedelta(days=2), 5, 0, d) == (1, d, 0)   # missed day, no freeze -> reset
    assert f(d - timedelta(days=3), 5, 2, d) == (1, d, 2)   # 2+ days missed -> reset, freezes kept
    assert f(d, 5, 1, d - timedelta(days=1)) == (5, d, 1)   # backwards clock -> no-op, keep later date
