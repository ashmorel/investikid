from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.models.user import User, UserProgress
from app.services.revise_service import _concept_of

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def auth_client(db_session, client):
    user = User(
        email="ai@example.com", username="aikid",
        password_hash=hash_password("TestPassword123!"),
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(user_id=user.id)
    db_session.add(progress)
    module = Module(
        topic="stocks", title="What is a Stock?",
        country_codes=[], is_premium=False, order_index=0, icon="📈",
    )
    db_session.add(module)
    await db_session.flush()
    quiz = Lesson(
        module_id=module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "What is a stock?",
            "choices": ["A loan", "A slice of a company", "A bond"],
            "answer_index": 1,
            "explanation": "A stock is a tiny piece of a company.",
        },
    )
    db_session.add(quiz)
    await db_session.flush()

    # Log in
    response = await client.post("/auth/login", json={
        "email": "ai@example.com", "password": "TestPassword123!",
    })
    assert response.status_code == 200

    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    return client, user, module, quiz


async def test_get_recommendations(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert "continue_learning" in data
    assert "practise_again" in data
    assert "something_new" in data
    assert "review_summary" in data


async def test_get_mastery_profile(auth_client):
    client, user, module, quiz = auth_client
    response = await client.get("/profile/mastery")
    assert response.status_code == 200
    data = response.json()
    assert "topics" in data
    assert "weak_concepts" in data


async def test_practice_quiz_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=(
        '{"question": "New Q", "choices": ["A", "B", "C"], "answer_index": 0, "explanation": "E"}'
    ))

    with patch("app.services.ai_content_service.get_llm_client", return_value=mock_client):
        response = await client.post(
            f"/lessons/{quiz.id}/practice",
            json={"wrong_answer_index": 0},
        )
    assert response.status_code == 200
    data = response.json()
    assert "question" in data
    assert "choices" in data


async def test_tutor_chat_endpoint(auth_client):
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value="A stock is a small piece of a company!")

    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/chat", json={
            "lesson_id": str(quiz.id),
            "message": "What is a stock?",
        })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data
    assert "messages_remaining" in data


async def test_tutor_chat_returns_503_on_llm_outage(auth_client):
    """An LLM provider outage is transient — the tutor endpoint must return 503
    (retryable), not a 500."""
    from app.services.llm_client import LLMError
    client, user, module, quiz = auth_client
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=LLMError("provider down"))
    with patch("app.services.tutor_service.get_llm_client", return_value=mock_client):
        response = await client.post("/tutor/chat", json={
            "lesson_id": str(quiz.id),
            "message": "What is a stock?",
        })
    assert response.status_code == 503


async def test_practice_and_tutor_reject_unpublished_lesson(auth_client, db_session):
    """A child holding a lesson_id whose module is unpublished (e.g. a retired
    curriculum after a live-market regeneration) must be rejected from both
    practice and tutor — they gate on is_module_visible like the content routes."""
    client, user, _module, _quiz = auth_client
    staged_module = Module(
        topic="stocks", title="Staged module", country_codes=[],
        is_premium=False, order_index=99, icon="📈", published=False,
    )
    db_session.add(staged_module)
    await db_session.flush()
    staged_quiz = Lesson(
        module_id=staged_module.id, type="quiz", xp_reward=25, order_index=0,
        content_json={
            "question": "Q", "choices": ["A", "B"], "answer_index": 0, "explanation": "E",
        },
    )
    db_session.add(staged_quiz)
    await db_session.flush()

    r1 = await client.post(
        f"/lessons/{staged_quiz.id}/practice", json={"wrong_answer_index": 0}
    )
    assert r1.status_code == 404

    r2 = await client.post(
        "/tutor/chat", json={"lesson_id": str(staged_quiz.id), "message": "hi"}
    )
    assert r2.status_code == 404


# ---------------------------------------------------------------------------
# Finding 1 — concept derivation parity between practice path and revise path
# ---------------------------------------------------------------------------

async def test_concept_of_tagged_lesson_returns_concept_name(db_session):
    """For a lesson with a taxonomy concept linked, _concept_of returns the
    Concept.name — matching what the revise path produces when loaded with
    selectinload(Lesson.concept)."""
    from sqlalchemy import select

    concept = Concept(
        topic="stocks",
        slug=f"parity-tagged-{__import__('uuid').uuid4().hex[:8]}",
        name="Concept Parity Name",
        blurb="test",
        difficulty_tier=1,
        order_index=0,
    )
    db_session.add(concept)
    await db_session.flush()

    mod = Module(
        topic="stocks", title="Parity Mod", country_codes=[],
        is_premium=False, order_index=99, icon="📈", published=True,
    )
    db_session.add(mod)
    await db_session.flush()

    lesson = Lesson(
        module_id=mod.id, type="quiz", xp_reward=10, order_index=0,
        content_json={"question": "What is a stock?"},
        concept_id=concept.id,
    )
    db_session.add(lesson)
    await db_session.commit()

    # Reload with selectinload so the relationship is in memory (as both the
    # practice path and revise path now do).
    loaded = await db_session.scalar(
        select(Lesson)
        .where(Lesson.id == lesson.id)
        .options(selectinload(Lesson.concept))
    )
    assert loaded is not None

    # Both paths must agree: the concept name, NOT the content_json question.
    result = _concept_of(loaded)
    assert result == "Concept Parity Name"


async def test_concept_of_untagged_lesson_returns_legacy_text(db_session):
    """For a lesson with no taxonomy concept, _concept_of returns the legacy
    content_json derivation — same as what the old practice path produced."""
    mod = Module(
        topic="stocks", title="Legacy Parity Mod", country_codes=[],
        is_premium=False, order_index=98, icon="📈", published=True,
    )
    db_session.add(mod)
    await db_session.flush()

    lesson = Lesson(
        module_id=mod.id, type="quiz", xp_reward=10, order_index=0,
        content_json={"question": "Legacy question text?"},
        concept_id=None,
    )
    db_session.add(lesson)
    await db_session.commit()

    # Even with selectinload, concept is None for an untagged lesson.
    from sqlalchemy import select
    loaded = await db_session.scalar(
        select(Lesson)
        .where(Lesson.id == lesson.id)
        .options(selectinload(Lesson.concept))
    )
    assert loaded is not None

    result = _concept_of(loaded)
    # Must match the legacy derivation: question field takes priority.
    assert result == "Legacy question text?"
