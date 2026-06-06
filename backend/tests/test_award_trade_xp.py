import uuid
from datetime import date

from app.models.user import UserProgress
from app.services.simulator_rewards import award_trade_xp
from app.services.simulator_rewards_config import SIM_XP_DAILY_CAP, SIM_XP_PER_TRADE


def _progress(xp=0, sim_date=None, sim_today=0):
    return UserProgress(user_id=uuid.uuid4(), xp=xp, sim_xp_date=sim_date, sim_xp_today=sim_today)


def test_first_trade_of_day_awards_full():
    up = _progress()
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == SIM_XP_PER_TRADE
    assert up.xp == SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 6)


def test_cap_blocks_further_xp_same_day():
    up = _progress(xp=SIM_XP_DAILY_CAP, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == 0
    assert up.xp == SIM_XP_DAILY_CAP


def test_partial_award_up_to_cap():
    up = _progress(xp=SIM_XP_DAILY_CAP - 2, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP - 2)
    awarded = award_trade_xp(up, date(2026, 6, 6))
    assert awarded == 2  # only enough to reach the cap
    assert up.sim_xp_today == SIM_XP_DAILY_CAP


def test_new_day_resets_counter():
    up = _progress(xp=SIM_XP_DAILY_CAP, sim_date=date(2026, 6, 6), sim_today=SIM_XP_DAILY_CAP)
    awarded = award_trade_xp(up, date(2026, 6, 7))
    assert awarded == SIM_XP_PER_TRADE
    assert up.sim_xp_today == SIM_XP_PER_TRADE
    assert up.sim_xp_date == date(2026, 6, 7)
