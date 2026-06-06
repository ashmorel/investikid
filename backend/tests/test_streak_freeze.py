from datetime import date

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
