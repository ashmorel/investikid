import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.apply_mission import ApplyMission
from app.models.content import Lesson, Level, Module
from app.models.simulator import Holding, Portfolio
from app.models.user import User, UserProgress
from app.services.app_settings import (
    get_investing_mission_cash,
    set_investing_mission_cash,
)
from app.services.investing_missions import mission_spec_for_title, sync_investing_missions
from app.services.simulator_rewards import evaluate_apply_missions

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session, *, title, market="GB", n_levels=2, lessons_per_level=3,
                  published=True):
    mod = Module(topic="t", title=title, market_code=market, order_index=0,
                 published=published, icon="📈", min_age=10, max_age=14)
    db_session.add(mod)
    await db_session.flush()
    final_lesson = None
    for li in range(n_levels):
        lvl = Level(module_id=mod.id, title=f"L{li}", order_index=li)
        db_session.add(lvl)
        await db_session.flush()
        for ji in range(lessons_per_level):
            lesson = Lesson(module_id=mod.id, level_id=lvl.id, type="quiz",
                            content_json={"q": f"{li}-{ji}"}, xp_reward=10, order_index=ji)
            db_session.add(lesson)
            await db_session.flush()
            final_lesson = lesson  # last flush = highest level, highest order
    return mod, final_lesson


def test_title_classification():
    assert mission_spec_for_title("Growing Money & Compound Interest")[0] == "first_buy"
    assert mission_spec_for_title("Investing Basics & Compound Growth")[0] == "first_buy"
    assert mission_spec_for_title("Risk & Diversification")[0] == "diversify"
    assert mission_spec_for_title("Risk, Diversification & Decision Making")[0] == "diversify"
    assert mission_spec_for_title("Spending & Budgeting") is None
    assert mission_spec_for_title("Banking & Accounts") is None


async def test_sync_attaches_mission_to_final_lesson_of_investing_modules(db_session):
    _, growth_final = await _module(db_session, title="Growing Money & Compound Interest")
    _, risk_final = await _module(db_session, title="Risk & Diversification")
    await _module(db_session, title="Spending & Budgeting")  # non-investing → skipped

    summary = await sync_investing_missions(db_session, market_code="GB")
    assert summary["created"] == 2

    missions = (await db_session.execute(select(ApplyMission))).scalars().all()
    by_lesson = {m.lesson_id: m for m in missions}
    assert growth_final.id in by_lesson and risk_final.id in by_lesson
    assert by_lesson[growth_final.id].mission_type == "first_buy"
    assert by_lesson[risk_final.id].mission_type == "diversify"
    assert by_lesson[risk_final.id].params_json == {"n": 3}


async def test_sync_is_idempotent(db_session):
    _, final = await _module(db_session, title="Investing Basics")
    first = await sync_investing_missions(db_session, market_code="GB")
    second = await sync_investing_missions(db_session, market_code="GB")
    assert first["created"] == 1
    assert second["created"] == 0 and second["updated"] == 1
    n = await db_session.scalar(
        select(func.count(ApplyMission.id)).where(ApplyMission.lesson_id == final.id)
    )
    assert n == 1


async def test_sync_uses_configured_cash(db_session):
    _, final = await _module(db_session, title="Growing Money", market="GB")
    await set_investing_mission_cash(db_session, {"GB": Decimal("42.50")})
    await sync_investing_missions(db_session, market_code="GB")
    mission = (await db_session.execute(
        select(ApplyMission).where(ApplyMission.lesson_id == final.id)
    )).scalars().one()
    assert mission.cash_reward == Decimal("42.50")
    assert mission.xp_reward == 20


async def test_sync_respects_market_filter(db_session):
    await _module(db_session, title="Growing Money", market="US")
    summary = await sync_investing_missions(db_session, market_code="GB")
    assert summary["created"] == 0  # the only investing module is US


async def test_get_investing_mission_cash_defaults(db_session):
    cash = await get_investing_mission_cash(db_session)
    assert cash["HK"] == Decimal("1000.00")
    assert cash["GB"] == Decimal("100.00")


async def _child(db_session, market):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"c{suffix}@x.test", username=f"child{suffix}", password_hash="x",
                dob=date(2012, 1, 1), country_code=market, currency_code="GBP",
                home_market_code=market, active_market_code=market)
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code="GBP")
    db_session.add_all([progress, portfolio])
    await db_session.flush()
    return user, progress, portfolio


async def test_market_scoping_blocks_cross_market_completion(db_session):
    # A GB-market mission must NOT complete for a US-market child's first buy.
    _, final = await _module(db_session, title="Growing Money", market="GB")
    await sync_investing_missions(db_session, market_code="GB")
    user, progress, portfolio = await _child(db_session, "US")
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()

    completed = await evaluate_apply_missions(
        db_session, user.id, progress, portfolio, market_code="US"
    )
    assert completed == []          # GB mission is out of scope for the US child
    assert progress.xp == 0

    # The same buy DOES complete it for a GB child.
    gb_user, gb_progress, gb_portfolio = await _child(db_session, "GB")
    db_session.add(Holding(portfolio_id=gb_portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    completed = await evaluate_apply_missions(
        db_session, gb_user.id, gb_progress, gb_portfolio, market_code="GB"
    )
    assert [c.lesson_id for c in completed] == [final.id]
    assert gb_progress.xp == 20
