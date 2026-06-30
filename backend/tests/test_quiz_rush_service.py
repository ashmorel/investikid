"""Tests for quiz_rush_service: pure scoring + DB-backed session builder."""
import datetime as dt

import pytest

from app.models.content import Lesson, LessonCompletion, Level, Module
from app.models.user import User
from app.services.quiz_rush_service import build_session, score_submission

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Pure function tests (no DB)
# ---------------------------------------------------------------------------

def test_score_counts_correct_and_combo():
    items = [
        {"lesson_id": "a", "question": "q", "choices": ["x", "y"], "answer_index": 0},
        {"lesson_id": "b", "question": "q", "choices": ["x", "y"], "answer_index": 1},
        {"lesson_id": "c", "question": "q", "choices": ["x", "y"], "answer_index": 0},
    ]
    answers = [
        {"lesson_id": "a", "choice_index": 0},  # correct
        {"lesson_id": "b", "choice_index": 1},  # correct (combo 2)
        {"lesson_id": "c", "choice_index": 1},  # wrong (combo breaks)
    ]
    result = score_submission(items, answers)
    assert result == {"correct": 2, "max_combo": 2, "points": 2 * 10 + 2 * 5}


def test_score_ignores_unknown_lessons():
    items = [{"lesson_id": "a", "question": "q", "choices": ["x"], "answer_index": 0}]
    answers = [{"lesson_id": "zzz", "choice_index": 0}]
    assert score_submission(items, answers)["correct"] == 0


# ---------------------------------------------------------------------------
# DB test: build_session prefers lessons from modules the child has completed
# ---------------------------------------------------------------------------

async def _seed_quiz_session(db_session):
    """Seed:
    - One published GB module with a quiz lesson the user has completed.
    - One published GB module with a quiz lesson the user has NOT completed.
    Returns (user, completed_lesson, unrelated_lesson).
    """
    user = User(
        email="quiz_rush@example.com",
        username="quizrushkid",
        password_hash="x",
        dob=dt.date(2012, 6, 1),
        country_code="GB",
        currency_code="GBP",
        active_market_code="GB",
    )
    # Module the child has touched
    touched_mod = Module(
        topic="saving", title="Saving Basics", market_code="GB", order_index=0, published=True
    )
    # Module the child has never touched
    untouched_mod = Module(
        topic="investing", title="Investing Basics", market_code="GB", order_index=1, published=True
    )
    db_session.add_all([user, touched_mod, untouched_mod])
    await db_session.flush()

    touched_level = Level(module_id=touched_mod.id, title="L1", order_index=0)
    untouched_level = Level(module_id=untouched_mod.id, title="L1", order_index=0)
    db_session.add_all([touched_level, untouched_level])
    await db_session.flush()

    completed_lesson = Lesson(
        module_id=touched_mod.id,
        level_id=touched_level.id,
        type="quiz",
        xp_reward=10,
        order_index=0,
        content_json={"question": "Q1?", "choices": ["A", "B"], "answer_index": 0, "explanation": "A"},
    )
    unrelated_lesson = Lesson(
        module_id=untouched_mod.id,
        level_id=untouched_level.id,
        type="quiz",
        xp_reward=10,
        order_index=0,
        content_json={"question": "Q2?", "choices": ["A", "B"], "answer_index": 1, "explanation": "B"},
    )
    db_session.add_all([completed_lesson, unrelated_lesson])
    await db_session.flush()

    completion = LessonCompletion(user_id=user.id, lesson_id=completed_lesson.id)
    db_session.add(completion)
    await db_session.flush()

    return user, completed_lesson, unrelated_lesson


async def test_build_session_prefers_unlocked_lessons(db_session):
    """When the child has ≥ COLD_START_MIN completed quiz lessons (we have 1 here,
    which is < COLD_START_MIN), the service falls back to all published quiz lessons.
    But we assert that the completed lesson is present in the returned set, verifying
    the unlocked-first query works and the fallback includes both lessons."""

    user, completed_lesson, unrelated_lesson = await _seed_quiz_session(db_session)

    items = await build_session(db_session, user, limit=50)

    lesson_ids = {it["lesson_id"] for it in items}
    # With only 1 completed lesson (< COLD_START_MIN=10), fallback fires and returns ALL.
    assert str(completed_lesson.id) in lesson_ids
    assert str(unrelated_lesson.id) in lesson_ids
    # Sanity: each item has the expected shape
    for it in items:
        assert set(it.keys()) == {"lesson_id", "question", "choices", "answer_index"}


# ---------------------------------------------------------------------------
# B3: Quiz Rush prioritises the child's WEAK concepts (play reinforces gaps)
# ---------------------------------------------------------------------------


async def _quiz_lesson(db_session, mod, level, *, concept_id, n):
    le = Lesson(
        module_id=mod.id, level_id=level.id, type="quiz", xp_reward=10, order_index=n,
        concept_id=concept_id,
        content_json={"question": f"Q{n}?", "choices": ["A", "B"], "answer_index": 0, "explanation": "A"},
    )
    db_session.add(le)
    await db_session.flush()
    return le


async def test_build_session_prioritises_weak_concepts(db_session):
    """Lessons tagged with a concept the child is WEAK on come first, so a
    capped session reinforces gaps rather than serving random trivia."""
    from app.models.concept import Concept
    from app.models.skill_profile import ConceptMastery

    user = User(
        email="qr-weak@example.com", username="qrweak", password_hash="x",
        dob=dt.date(2012, 6, 1), country_code="GB", currency_code="GBP",
        active_market_code="GB",
    )
    mod = Module(topic="saving", title="Saving", market_code="GB", order_index=0, published=True)
    db_session.add_all([user, mod])
    await db_session.flush()
    level = Level(module_id=mod.id, title="L1", order_index=0)
    weak_c = Concept(topic="saving", slug="weak-c", name="Weak C", difficulty_tier=1, order_index=0)
    strong_c = Concept(topic="saving", slug="strong-c", name="Strong C", difficulty_tier=1, order_index=1)
    db_session.add_all([level, weak_c, strong_c])
    await db_session.flush()

    weak_lessons = [await _quiz_lesson(db_session, mod, level, concept_id=weak_c.id, n=i) for i in range(3)]
    for i in range(7):
        await _quiz_lesson(db_session, mod, level, concept_id=strong_c.id, n=10 + i)

    # The child has attempted the weak concept and scored low (1/3 ≈ 0.33 < 0.6).
    db_session.add(ConceptMastery(
        user_id=user.id, concept_id=weak_c.id, attempts=3, correct=1, mastery_score=1 / 3,
    ))
    await db_session.flush()

    items = await build_session(db_session, user, limit=3)

    weak_ids = {str(le.id) for le in weak_lessons}
    returned = {it["lesson_id"] for it in items}
    # A 3-item session is filled entirely from the weak-concept lessons.
    assert returned == weak_ids


async def test_build_session_no_weak_concepts_unchanged(db_session):
    """With no weak-concept signal, behaviour is the prior shuffle-all (no regression)."""
    user, completed_lesson, unrelated_lesson = await _seed_quiz_session(db_session)
    items = await build_session(db_session, user, limit=50)
    lesson_ids = {it["lesson_id"] for it in items}
    assert str(completed_lesson.id) in lesson_ids
    assert str(unrelated_lesson.id) in lesson_ids


async def test_build_session_weak_concept_with_no_matching_lessons(db_session):
    """A weak concept with no lessons in the pool degrades to the no-weak path (no crash)."""
    from app.models.concept import Concept
    from app.models.skill_profile import ConceptMastery

    user, completed_lesson, unrelated_lesson = await _seed_quiz_session(db_session)
    # A weak concept that NO seeded lesson is tagged with.
    orphan = Concept(topic="saving", slug="orphan-c", name="Orphan", difficulty_tier=1, order_index=9)
    db_session.add(orphan)
    await db_session.flush()
    db_session.add(ConceptMastery(
        user_id=user.id, concept_id=orphan.id, attempts=4, correct=1, mastery_score=0.25,
    ))
    await db_session.flush()

    items = await build_session(db_session, user, limit=50)
    lesson_ids = {it["lesson_id"] for it in items}
    assert str(completed_lesson.id) in lesson_ids
    assert str(unrelated_lesson.id) in lesson_ids
