import datetime
import uuid
from decimal import Decimal

import pytest

from app.models.content import Lesson, LessonCompletion, Module
from app.models.simulator import Portfolio
from app.models.user import User
from app.services.content_service import grant_module_completion_cash

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _setup(db_session, reward, n_lessons=2):
    user = User(
        username=f"c{uuid.uuid4().hex[:8]}",
        email=f"c{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=datetime.date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    portfolio = Portfolio(user_id=user.id, virtual_cash=Decimal("1000.00"), currency_code="GBP")
    module = Module(topic="stocks", title="S", order_index=1, completion_cash_reward=reward)
    db_session.add_all([portfolio, module])
    await db_session.flush()
    lessons = [
        Lesson(module_id=module.id, type="card", content_json={}, xp_reward=10, order_index=i)
        for i in range(n_lessons)
    ]
    db_session.add_all(lessons)
    await db_session.flush()
    return user, portfolio, module, lessons


async def test_no_grant_until_all_lessons_done(db_session):
    user, portfolio, module, lessons = await _setup(db_session, Decimal("250.00"))
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lessons[0].id))
    await db_session.flush()
    granted = await grant_module_completion_cash(db_session, user.id, module.id)
    assert granted is False
    assert portfolio.virtual_cash == Decimal("1000.00")


async def test_grant_on_full_completion_once(db_session):
    user, portfolio, module, lessons = await _setup(db_session, Decimal("250.00"))
    db_session.add_all([LessonCompletion(user_id=user.id, lesson_id=ls.id) for ls in lessons])
    await db_session.flush()
    assert await grant_module_completion_cash(db_session, user.id, module.id) is True
    assert portfolio.virtual_cash == Decimal("1250.00")
    assert await grant_module_completion_cash(db_session, user.id, module.id) is False
    assert portfolio.virtual_cash == Decimal("1250.00")


async def test_no_reward_configured_is_noop(db_session):
    user, portfolio, module, lessons = await _setup(db_session, None)
    db_session.add_all([LessonCompletion(user_id=user.id, lesson_id=ls.id) for ls in lessons])
    await db_session.flush()
    assert await grant_module_completion_cash(db_session, user.id, module.id) is False
