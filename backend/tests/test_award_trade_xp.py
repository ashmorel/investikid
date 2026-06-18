"""award_trade_xp — capped trade XP seam (C2a Task 3)."""
from datetime import date

import pytest

from app.models.user import UserProgress
from app.services.simulator_rewards import award_trade_xp
from app.services.simulator_rewards_config import SIM_XP_DAILY_CAP, SIM_XP_PER_TRADE

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _progress(db_session, user, *, xp=0, sim_date=None, sim_today=0):
    """Fetch or create a UserProgress for an existing user."""
    p = await db_session.get(UserProgress, user.id)
    if p is None:
        p = UserProgress(user_id=user.id, xp=xp, sim_xp_date=sim_date, sim_xp_today=sim_today)
        db_session.add(p)
        await db_session.flush()
    else:
        p.xp = xp
        p.sim_xp_date = sim_date
        p.sim_xp_today = sim_today
    return p


async def test_first_trade_of_day_awards_full(db_session, user_with_module):
    user, *_ = user_with_module
    up = await _progress(db_session, user)
    start_xp = up.xp
    awarded = await award_trade_xp(db_session, up, date(2026, 6, 6))
    assert awarded == SIM_XP_PER_TRADE
    assert up.xp == start_xp + SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 6)


async def test_cap_blocks_further_xp_same_day(db_session, user_with_module):
    user, *_ = user_with_module
    up = await _progress(db_session, user, xp=SIM_XP_DAILY_CAP,
                         sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    xp_before = up.xp
    awarded = await award_trade_xp(db_session, up, date(2026, 6, 6))
    assert awarded == 0
    assert up.xp == xp_before


async def test_partial_award_up_to_cap(db_session, user_with_module):
    user, *_ = user_with_module
    up = await _progress(db_session, user, xp=0,
                         sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP - 2)
    awarded = await award_trade_xp(db_session, up, date(2026, 6, 6))
    assert awarded == 2  # only enough to reach the cap
    assert up.sim_xp_today == SIM_XP_DAILY_CAP


async def test_new_day_resets_counter(db_session, user_with_module):
    user, *_ = user_with_module
    up = await _progress(db_session, user, xp=SIM_XP_DAILY_CAP,
                         sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    awarded = await award_trade_xp(db_session, up, date(2026, 6, 7))
    assert awarded == SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 7)
