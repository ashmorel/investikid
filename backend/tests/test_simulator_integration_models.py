import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.apply_mission import ApplyMission, ApplyMissionCompletion  # noqa: F401
from app.models.cash_grant import CashGrant
from app.models.content import Lesson, Module
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _module(db_session):
    m = Module(topic="stocks", title="Stocks 101", order_index=1)
    db_session.add(m)
    await db_session.flush()
    return m


async def _user(db_session):
    u = User(
        email=f"{uuid.uuid4().hex}@example.com", username=uuid.uuid4().hex[:20],
        password_hash="x", dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_apply_mission_unique_per_lesson(db_session):
    m = await _module(db_session)
    lesson = Lesson(module_id=m.id, type="card", content_json={}, xp_reward=10, order_index=1)
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(ApplyMission(lesson_id=lesson.id, mission_type="first_buy", params_json={},
                                title="Buy a share", prompt="Try buying one!", xp_reward=20))
    await db_session.flush()
    db_session.add(ApplyMission(lesson_id=lesson.id, mission_type="first_sell", params_json={},
                                title="Sell", prompt="Sell one", xp_reward=20))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_cash_grant_unique_source(db_session):
    user = await _user(db_session)
    src = uuid.uuid4()
    db_session.add(CashGrant(user_id=user.id, source_type="module", source_id=src,
                             currency_code="GBP", amount=Decimal("250.00")))
    await db_session.flush()
    db_session.add(CashGrant(user_id=user.id, source_type="module", source_id=src,
                             currency_code="GBP", amount=Decimal("250.00")))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_user_progress_has_sim_xp_columns(db_session):
    user = await _user(db_session)
    up = UserProgress(user_id=user.id)
    db_session.add(up)
    await db_session.flush()
    assert up.sim_xp_today == 0
    assert up.sim_xp_date is None


async def test_module_completion_cash_reward_nullable(db_session):
    m = await _module(db_session)
    assert m.completion_cash_reward is None
