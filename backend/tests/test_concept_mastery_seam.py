"""TDD — Task 2: record_concept_attempt wired into the lesson-completion seam.

These tests cover the three guard conditions:
  1. Quiz + concept_id + score >= 0.5  → ConceptMastery row (correct=1)
  2. Quiz + concept_id + score < 0.5   → ConceptMastery row (correct=0)
  3. Quiz + concept_id=None            → NO ConceptMastery row; TopicMastery still updates
  4. Non-quiz (card) + concept_id      → NO ConceptMastery row
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.models.skill_profile import ConceptMastery, TopicMastery
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

_REGISTER_URL = "/auth/register"
_LOGIN_URL = "/auth/login"


def _user_payload(suffix: str) -> dict:
    return {
        "email": f"seam_{suffix}@example.com",
        "username": f"seam_{suffix}",
        "password": "SecurePass123!",
        "dob": "2012-06-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": "parent@example.com",
    }


async def _login(client, suffix: str) -> None:
    payload = _user_payload(suffix)
    await client.post(_REGISTER_URL, json=payload)
    await client.post(_LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


@pytest_asyncio.fixture
async def concept_and_module(db_session):
    """A Concept + a free Module referencing it."""
    concept = Concept(
        topic="savings",
        slug=f"slug_seam_{uuid.uuid4().hex[:8]}",
        name="Compound Interest",
        difficulty_tier=1,
        order_index=0,
    )
    module = Module(
        topic="savings",
        title="Savings Seam",
        country_codes=[],
        is_premium=False,
        order_index=99,
        market_code="GB",
    )
    db_session.add_all([concept, module])
    await db_session.flush()
    return concept, module


async def test_correct_quiz_with_concept_id_creates_mastery_row(client, db_session, concept_and_module):
    """Quiz lesson tagged with concept_id, score >= 0.5 → ConceptMastery row with correct=1."""
    concept, module = concept_and_module

    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=25,
        order_index=0,
        concept_id=concept.id,
        content_json={"question": "q?", "choices": ["A", "B"], "answer_index": 0, "explanation": "e"},
    )
    db_session.add(lesson)
    await db_session.flush()

    suffix = uuid.uuid4().hex[:8]
    await _login(client, suffix)

    r = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 0.9})
    assert r.status_code == 200, r.text
    assert r.json()["already_completed"] is False

    # Fetch the user
    user = await db_session.scalar(
        select(User).where(User.email == f"seam_{suffix}@example.com")
    )
    assert user is not None

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row is not None, "ConceptMastery row should have been created"
    assert row.attempts == 1
    assert row.correct == 1
    assert row.mastery_score == 1.0


async def test_wrong_quiz_with_concept_id_creates_row_correct_zero(client, db_session, concept_and_module):
    """Quiz lesson tagged with concept_id, score < 0.5 → ConceptMastery row with correct=0."""
    concept, module = concept_and_module

    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=25,
        order_index=1,
        concept_id=concept.id,
        content_json={"question": "q2?", "choices": ["A", "B"], "answer_index": 0, "explanation": "e"},
    )
    db_session.add(lesson)
    await db_session.flush()

    suffix = uuid.uuid4().hex[:8]
    await _login(client, suffix)

    r = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 0.2})
    assert r.status_code == 200, r.text

    user = await db_session.scalar(
        select(User).where(User.email == f"seam_{suffix}@example.com")
    )
    assert user is not None

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row is not None, "ConceptMastery row should have been created for a wrong attempt"
    assert row.attempts == 1
    assert row.correct == 0
    assert row.mastery_score == 0.0


async def test_quiz_without_concept_id_no_concept_mastery_but_topic_mastery_updates(
    client, db_session, concept_and_module
):
    """Quiz lesson with concept_id=None → NO ConceptMastery row; TopicMastery still accrues."""
    _, module = concept_and_module

    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        xp_reward=25,
        order_index=2,
        concept_id=None,  # untagged
        content_json={"question": "q3?", "choices": ["A", "B"], "answer_index": 0, "explanation": "e"},
    )
    db_session.add(lesson)
    await db_session.flush()

    suffix = uuid.uuid4().hex[:8]
    await _login(client, suffix)

    r = await client.post(f"/lessons/{lesson.id}/complete", json={"score": 0.8})
    assert r.status_code == 200, r.text

    user = await db_session.scalar(
        select(User).where(User.email == f"seam_{suffix}@example.com")
    )
    assert user is not None

    # No ConceptMastery rows at all for this user
    concept_rows = (
        await db_session.scalars(
            select(ConceptMastery).where(ConceptMastery.user_id == user.id)
        )
    ).all()
    assert concept_rows == [], "Untagged lesson must NOT create any ConceptMastery row"

    # TopicMastery must still be updated
    topic_row = await db_session.get(TopicMastery, (user.id, "savings"))
    assert topic_row is not None, "TopicMastery must still accrue for untagged quizzes"
    assert topic_row.quizzes_attempted == 1
    assert topic_row.quizzes_correct == 1


async def test_card_lesson_with_concept_id_no_concept_mastery(client, db_session, concept_and_module):
    """Non-quiz (card) lesson → correct is None → NO ConceptMastery row even if concept_id set."""
    concept, module = concept_and_module

    lesson = Lesson(
        module_id=module.id,
        type="card",
        xp_reward=10,
        order_index=3,
        concept_id=concept.id,
        content_json={"title": "Card with concept", "body": "body text"},
    )
    db_session.add(lesson)
    await db_session.flush()

    suffix = uuid.uuid4().hex[:8]
    await _login(client, suffix)

    r = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r.status_code == 200, r.text

    user = await db_session.scalar(
        select(User).where(User.email == f"seam_{suffix}@example.com")
    )
    assert user is not None

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row is None, "Card lesson must NOT create a ConceptMastery row"
