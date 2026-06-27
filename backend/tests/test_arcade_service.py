import uuid
from datetime import date

import pytest

from app.models.user import User, UserProgress
from app.services import arcade_service as svc

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _user(db_session, username=None, market="GB", *, handle=None, consent=True, hidden=False):
    if username is None:
        username = f"arcade_{uuid.uuid4().hex[:8]}"
    u = User(
        username=username,
        display_handle=handle or f"H_{username[:10]}",
        leaderboard_consent=consent,
        leaderboard_hidden=hidden,
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


async def test_leaderboard_is_per_market_ranked_and_privacy_gated(db_session):
    u1, _ = await _user(db_session, f"lb_a_{uuid.uuid4().hex[:6]}", "GB", handle="Alpha")
    u2, _ = await _user(db_session, f"lb_b_{uuid.uuid4().hex[:6]}", "GB", handle="Bravo")
    u3, _ = await _user(db_session, f"lb_c_{uuid.uuid4().hex[:6]}", "US", handle="Charlie")
    u4, _ = await _user(db_session, f"lb_d_{uuid.uuid4().hex[:6]}", "GB", handle="DeltaHidden", hidden=True)
    u5, _ = await _user(db_session, f"lb_e_{uuid.uuid4().hex[:6]}", "GB", handle="EchoNoConsent", consent=False)
    for u, pts in [(u1, 50), (u2, 90), (u3, 200), (u4, 70), (u5, 80)]:
        await svc.record_score(db_session, user_id=u.id, game="quiz_rush", points=pts,
                               market_code=u.active_market_code)
    board = await svc.weekly_leaderboard(db_session, game="quiz_rush", market_code="GB")
    names = [r[0] for r in board]
    # Shows the safe display_handle, ranked descending
    assert "Bravo" in names and "Alpha" in names
    assert names.index("Bravo") < names.index("Alpha")
    # Privacy gating
    assert "Charlie" not in names        # other market excluded
    assert "DeltaHidden" not in names    # leaderboard_hidden honoured
    assert "EchoNoConsent" not in names  # no parental consent
    # The raw username must NEVER appear on a public board
    for u in (u1, u2):
        assert u.username not in names


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
