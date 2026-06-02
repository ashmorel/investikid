import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import _MODULES, seed_modules_and_lessons

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_every_module_has_at_least_five_questions_or_scenarios():
    """Each module's level must offer >= 5 quiz/scenario lessons."""
    for spec in _MODULES:
        qs = [le for le in spec["lessons"] if le["type"] in ("quiz", "scenario")]
        assert len(qs) >= 5, (
            f"module {spec['title']!r} has only {len(qs)} quiz/scenario lessons (need >=5)"
        )


def test_quiz_and_scenario_specs_are_well_formed():
    for spec in _MODULES:
        for le in spec["lessons"]:
            cj = le["content_json"]
            if le["type"] == "quiz":
                assert cj.get("question"), f"empty quiz question in {spec['title']!r}"
                assert cj.get("explanation"), f"empty explanation in {spec['title']!r}"
                choices = cj.get("choices") or []
                assert len(choices) >= 2
                assert isinstance(cj.get("answer_index"), int)
                assert 0 <= cj["answer_index"] < len(choices), (
                    f"answer_index out of range in {spec['title']!r}"
                )
            elif le["type"] == "scenario":
                assert cj.get("prompt"), f"empty scenario prompt in {spec['title']!r}"
                choices = cj.get("choices") or []
                assert len(choices) >= 2
                assert isinstance(cj.get("correct_index"), int)
                assert 0 <= cj["correct_index"] < len(choices)
                for ch in choices:
                    assert ch.get("label") and ch.get("outcome"), (
                        f"scenario choice missing label/outcome in {spec['title']!r}"
                    )


async def _count_lessons_for(session, topic, title) -> int:
    module = await session.scalar(
        select(Module).where(Module.topic == topic, Module.title == title)
    )
    assert module is not None
    return await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.module_id == module.id)
    )


async def test_seed_is_idempotent_and_meets_criterion(db_session):
    # First seed creates everything.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    spec = _MODULES[0]
    count_after_first = await _count_lessons_for(db_session, spec["topic"], spec["title"])
    assert count_after_first == len(spec["lessons"])

    # A level should expose >= 5 quiz/scenario lessons.
    module = await db_session.scalar(
        select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
    )
    level = await db_session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 0)
    )
    lessons = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).all()
    qs = [le for le in lessons if le.type in ("quiz", "scenario")]
    assert len(qs) >= 5

    # Second seed must add nothing (idempotent).
    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    count_after_second = await _count_lessons_for(db_session, spec["topic"], spec["title"])
    assert count_after_second == count_after_first
