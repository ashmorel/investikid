import pytest

from app.models.market_progress import UserMarketProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_user_market_progress_composite_pk(db_session, user_with_module):
    user, *_ = user_with_module
    ump = UserMarketProgress(user_id=user.id, market_code="GB", xp=40)
    db_session.add(ump)
    await db_session.flush()
    fetched = await db_session.get(UserMarketProgress, (user.id, "GB"))
    assert fetched is not None
    assert fetched.xp == 40
    assert fetched.market_code == "GB"
