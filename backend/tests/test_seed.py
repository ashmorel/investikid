import pytest
from sqlalchemy import select, func
from app.models.content import Module, Lesson
from app.seed.content import seed_modules_and_lessons

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_creates_starter_content(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    module_count = await db_session.scalar(select(func.count()).select_from(Module))
    lesson_count = await db_session.scalar(select(func.count()).select_from(Lesson))
    assert module_count >= 3
    assert lesson_count >= 6


async def test_seed_is_idempotent(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    first = await db_session.scalar(select(func.count()).select_from(Module))

    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    second = await db_session.scalar(select(func.count()).select_from(Module))

    assert first == second
