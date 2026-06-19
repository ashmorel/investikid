import pytest

from app.services.app_settings import (
    get_market_completion_bonus_coins,
    get_market_enroll_bonus_coins,
    set_market_completion_bonus_coins,
    set_market_enroll_bonus_coins,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_enroll_bonus_defaults_then_settable(db_session):
    assert await get_market_enroll_bonus_coins(db_session) == 25
    await set_market_enroll_bonus_coins(db_session, 40)
    assert await get_market_enroll_bonus_coins(db_session) == 40


async def test_completion_bonus_defaults_then_settable(db_session):
    assert await get_market_completion_bonus_coins(db_session) == 250
    await set_market_completion_bonus_coins(db_session, 500)
    assert await get_market_completion_bonus_coins(db_session) == 500


async def test_negative_rejected(db_session):
    with pytest.raises(ValueError):
        await set_market_enroll_bonus_coins(db_session, -1)
