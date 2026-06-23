import uuid
from datetime import date

import pytest

from app.models.user import User, UserProgress
from app.services import arcade_service as svc

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, username=None, market="GB"):
    if username is None:
        username = f"arcade_{uuid.uuid4().hex[:8]}"
    u = User(
        username=username,
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code=market,
        currency_code="GBP",
        active_market_code=market,
    )
    db_session.add(u)
    await db_session.flush()
    p = UserProgress(user_id=u.id)
    db_session.add(p)
    await db_session.flush()
    return u, p


async def test_award_is_capped_per_day(db_session):
    u, p = await _user(db_session)
    first = await svc.award_arcade_coins(db_session, p, 20, market_code="GB")
    second = await svc.award_arcade_coins(db_session, p, 20, market_code="GB")
    assert first == 20
    assert second == 5            # only 5 of the cap (25) remained
    assert p.arcade_xp_today == 25


async def test_record_score_and_personal_best(db_session):
    u, p = await _user(db_session)
    await svc.record_score(db_session, user_id=u.id, game="quiz_rush", points=80, market_code="GB")
    await svc.record_score(db_session, user_id=u.id, game="quiz_rush", points=140, market_code="GB")
    assert await svc.personal_best(db_session, user_id=u.id, game="quiz_rush") == 140


async def test_leaderboard_is_per_market_and_ranked(db_session):
    u1, p1 = await _user(db_session, f"lb_a_{uuid.uuid4().hex[:6]}", "GB")
    u2, p2 = await _user(db_session, f"lb_b_{uuid.uuid4().hex[:6]}", "GB")
    u3, p3 = await _user(db_session, f"lb_c_{uuid.uuid4().hex[:6]}", "US")
    await svc.record_score(db_session, user_id=u1.id, game="quiz_rush", points=50, market_code="GB")
    await svc.record_score(db_session, user_id=u2.id, game="quiz_rush", points=90, market_code="GB")
    await svc.record_score(db_session, user_id=u3.id, game="quiz_rush", points=200, market_code="US")
    board = await svc.weekly_leaderboard(db_session, game="quiz_rush", market_code="GB")
    usernames = [r[0] for r in board]
    assert u2.username in usernames
    assert u1.username in usernames
    assert u3.username not in usernames            # US child excluded
    assert usernames.index(u2.username) < usernames.index(u1.username)  # ranked desc


async def test_personal_best_returns_zero_if_none(db_session):
    u, p = await _user(db_session)
    result = await svc.personal_best(db_session, user_id=u.id, game="quiz_rush")
    assert result == 0


async def test_day_rollover_resets_cap(db_session):
    u, p = await _user(db_session)
    yesterday = date(2020, 1, 1)
    p.arcade_xp_date = yesterday
    p.arcade_xp_today = 25  # already fully used yesterday
    await db_session.flush()
    today = date(2020, 1, 2)
    granted = await svc.award_arcade_coins(db_session, p, 10, market_code="GB", today=today)
    assert granted == 10
    assert p.arcade_xp_today == 10
    assert p.arcade_xp_date == today
