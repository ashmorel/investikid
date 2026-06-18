import pytest
from sqlalchemy import select

from app.models.market_progress import UserMarketProgress
from app.models.user import UserProgress
from app.services.market_progress_service import award_xp

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_award_xp_updates_global_and_active_market(db_session, user_with_module):
    user, *_ = user_with_module
    progress = await db_session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id, xp=0)
        db_session.add(progress)
        await db_session.flush()
    start = progress.xp

    gb_before = await db_session.get(UserMarketProgress, (user.id, "GB"))
    gb_start = gb_before.xp if gb_before is not None else 0

    await award_xp(db_session, progress, 25)
    await db_session.flush()

    assert progress.xp == start + 25
    gb = await db_session.get(UserMarketProgress, (user.id, "GB"))
    assert gb is not None and gb.xp == gb_start + 25


async def test_award_xp_invariant_across_two_markets(db_session, user_with_module):
    user, *_ = user_with_module
    progress = await db_session.get(UserProgress, user.id)
    if progress is None:
        progress = UserProgress(user_id=user.id, xp=0)
        db_session.add(progress)
        await db_session.flush()

    await award_xp(db_session, progress, 10, market_code="GB")
    await award_xp(db_session, progress, 7, market_code="US")
    await db_session.flush()

    rows = (await db_session.scalars(
        select(UserMarketProgress).where(UserMarketProgress.user_id == user.id)
    )).all()
    assert sum(r.xp for r in rows) == progress.xp  # invariant
