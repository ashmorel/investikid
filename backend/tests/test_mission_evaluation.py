import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.apply_mission import ApplyMission
from app.models.cash_grant import CashGrant
from app.models.content import Lesson, Module
from app.models.simulator import Holding, Portfolio
from app.models.user import User, UserProgress
from app.services.simulator_rewards import evaluate_apply_missions, grant_cash

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_child(db_session):
    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"c{suffix}@x.test",
        username=f"child{suffix}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code="GBP")
    db_session.add_all([progress, portfolio])
    await db_session.flush()
    return user, progress, portfolio


async def _mission(db_session, mtype, params, xp=20, cash=None):
    m = Module(topic="stocks", title="S", order_index=1)
    db_session.add(m)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add(lesson)
    await db_session.flush()
    mission = ApplyMission(lesson_id=lesson.id, mission_type=mtype, params_json=params,
                           title="t", prompt="p", xp_reward=xp, cash_reward=cash)
    db_session.add(mission)
    await db_session.flush()
    return mission


async def test_grant_cash_is_idempotent(db_session):
    user, _, portfolio = await _seed_child(db_session)
    src = uuid.uuid4()
    g1 = await grant_cash(db_session, user.id, portfolio, "module", src, Decimal("250.00"))
    g2 = await grant_cash(db_session, user.id, portfolio, "module", src, Decimal("250.00"))
    assert g1 is True and g2 is False
    assert portfolio.virtual_cash == Decimal("1250.00")
    rows = (await db_session.execute(select(CashGrant).where(CashGrant.user_id == user.id))).scalars().all()
    assert len(rows) == 1


async def test_first_buy_mission_completes_and_awards(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    mission = await _mission(db_session, "first_buy", {}, xp=20, cash=Decimal("100.00"))
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    completed = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert [c.id for c in completed] == [mission.id]
    assert progress.xp == 20
    assert portfolio.virtual_cash == Decimal("1100.00")


async def test_mission_not_recompleted(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    await _mission(db_session, "first_buy", {})
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    first = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    second = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert len(first) == 1
    assert second == []


async def test_diversify_not_complete_until_threshold(db_session):
    user, progress, portfolio = await _seed_child(db_session)
    await _mission(db_session, "diversify", {"n": 2})
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="AAPL", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("150")))
    await db_session.flush()
    assert await evaluate_apply_missions(db_session, user.id, progress, portfolio) == []
    db_session.add(Holding(portfolio_id=portfolio.id, ticker="MSFT", exchange="NASDAQ",
                           shares=Decimal("1"), avg_buy_price=Decimal("300")))
    await db_session.flush()
    completed = await evaluate_apply_missions(db_session, user.id, progress, portfolio)
    assert len(completed) == 1
