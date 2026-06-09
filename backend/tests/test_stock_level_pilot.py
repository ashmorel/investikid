import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import seed_modules_and_lessons

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _stock_levels(session):
    module = await session.scalar(
        select(Module).where(Module.topic == "stocks", Module.title == "What is a Stock?")
    )
    assert module is not None
    levels = (await session.scalars(
        select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
    )).all()
    return module, levels


async def _lesson_count(session, level):
    return await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.level_id == level.id)
    )


async def test_stock_module_has_three_levels(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    _module, levels = await _stock_levels(db_session)
    assert [lv.order_index for lv in levels] == [0, 1, 2]
    assert [lv.is_premium for lv in levels] == [False, False, True]  # L1-2 free, L3 premium
    assert levels[1].title == "Level 2" and levels[2].title == "Level 3"

    # L2 = 2 cards + 4 quizzes + 1 scenario = 7; L3 = 2 cards + 4 quizzes + 1 scenario = 7
    assert await _lesson_count(db_session, levels[1]) == 7
    assert await _lesson_count(db_session, levels[2]) == 7
