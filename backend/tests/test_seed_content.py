import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import (
    _MODULES,
    _insert_position,
    _lesson_identity,
    seed_modules_and_lessons,
)

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


def test_every_module_first_lesson_is_card():
    """Every module must open with a card (foundational intro)."""
    for spec in _MODULES:
        first = spec["lessons"][0]
        assert first["type"] == "card", (
            f"module {spec['title']!r}: first lesson is {first['type']!r}, expected 'card'"
        )


def test_scenarios_not_before_first_quiz():
    """Within each module, scenarios must not appear before the first quiz or card.

    Concretely: the index of the first scenario must be greater than the index of
    the first quiz (a light pedagogical-order guard).  Modules with no scenario or
    no quiz are skipped.
    """
    for spec in _MODULES:
        lessons = spec["lessons"]
        scenario_indices = [i for i, le in enumerate(lessons) if le["type"] == "scenario"]
        quiz_indices = [i for i, le in enumerate(lessons) if le["type"] == "quiz"]
        if not scenario_indices or not quiz_indices:
            continue
        first_scenario = scenario_indices[0]
        first_quiz = quiz_indices[0]
        assert first_scenario > first_quiz, (
            f"module {spec['title']!r}: first scenario (index {first_scenario}) "
            f"appears before first quiz (index {first_quiz})"
        )


def test_insert_position_slots_into_type_band():
    """A newly-appended lesson lands at the END of its difficulty band:
    cards -> video -> quizzes -> scenarios, without reordering existing lessons."""
    seq = ["card", "card", "video", "quiz", "scenario"]
    # A new card goes after the existing cards (index 2), before the video.
    assert _insert_position(seq, "card") == 2
    # A new video goes after the existing video (index 3).
    assert _insert_position(seq, "video") == 3
    # A new quiz goes after the existing quiz (index 4), before the scenario.
    assert _insert_position(seq, "quiz") == 4
    # A new scenario goes at the very end (index 5).
    assert _insert_position(seq, "scenario") == 5
    # Empty level -> position 0.
    assert _insert_position([], "quiz") == 0
    # All scenarios -> a new quiz slots in front of them.
    assert _insert_position(["scenario", "scenario"], "quiz") == 0


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

    # On a fresh DB the seeded order matches the curriculum spec exactly.
    lessons_after = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).all()
    by_ident = {_lesson_identity(le.type, le.content_json): le for le in lessons_after}
    for i, lesson_spec in enumerate(spec["lessons"]):
        ident = _lesson_identity(lesson_spec["type"], lesson_spec["content_json"])
        le = by_ident.get(ident)
        assert le is not None, f"lesson not found in DB: {ident!r}"
        assert le.order_index == i, (
            f"lesson {ident!r}: expected order_index={i}, got {le.order_index}"
        )


async def test_reseed_preserves_manual_reorder(db_session):
    """A manual admin reorder must survive re-seeding: the seeder only places
    new lessons, it never re-sorts lessons already positioned."""
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    spec = _MODULES[0]
    module = await db_session.scalar(
        select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
    )
    level = await db_session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 0)
    )
    lessons = list((await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())

    # Simulate an admin manually reversing the lesson order (via OrderArrows).
    reversed_lessons = list(reversed(lessons))
    for i, le in enumerate(reversed_lessons):
        le.order_index = i
    await db_session.flush()
    expected_order = [le.id for le in reversed_lessons]

    # Re-seed: must NOT reset to the curriculum order.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    after = list((await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())
    assert [le.id for le in after] == expected_order
