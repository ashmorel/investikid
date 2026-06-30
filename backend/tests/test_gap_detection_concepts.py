"""TDD tests for per-concept breakdown in get_strengths_and_gaps (Task 3)."""
import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.services.gap_detection_service import get_strengths_and_gaps

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def strengths_user_with_concepts(db_session):
    """Seed a user with TopicMastery + ConceptMastery rows for 'savings' topic.

    Two concepts under 'savings':
      - "compound-interest": mastery_score=0.9  (strong, attempts=3)
      - "apr":               mastery_score=0.5  (needs_practice, attempts=2)

    One concept under 'savings' with attempts=0 (should NOT appear).

    One concept under a different topic 'budgeting' with attempts=1 (should
    appear under budgeting TopicStrength, not savings).
    """
    from app.models.concept import Concept
    from app.models.skill_profile import ConceptMastery, TopicMastery
    from app.models.user import User

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"gaps_{uid}@example.com",
        username=f"gapskid_{uid}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()  # get user.id before FK rows

    # TopicMastery rows so the topic appears in all_topics
    tm_savings = TopicMastery(
        user_id=user.id,
        topic="savings",
        mastery_score=0.7,
        quizzes_attempted=5,
        quizzes_correct=3,
    )
    tm_budgeting = TopicMastery(
        user_id=user.id,
        topic="budgeting",
        mastery_score=0.4,
        quizzes_attempted=2,
        quizzes_correct=1,
    )
    db_session.add_all([tm_savings, tm_budgeting])

    # Concepts
    slug_prefix = uuid.uuid4().hex[:6]
    c_strong = Concept(
        topic="savings",
        slug=f"compound-interest-{slug_prefix}",
        name="Compound Interest",
        difficulty_tier=1,
        order_index=0,
    )
    c_weak = Concept(
        topic="savings",
        slug=f"apr-{slug_prefix}",
        name="APR",
        difficulty_tier=2,
        order_index=1,
    )
    c_zero = Concept(
        topic="savings",
        slug=f"inflation-{slug_prefix}",
        name="Inflation",
        difficulty_tier=1,
        order_index=2,
    )
    c_budget = Concept(
        topic="budgeting",
        slug=f"50-30-20-{slug_prefix}",
        name="50/30/20 Rule",
        difficulty_tier=1,
        order_index=0,
    )
    db_session.add_all([c_strong, c_weak, c_zero, c_budget])
    await db_session.flush()

    # ConceptMastery rows
    cm_strong = ConceptMastery(
        user_id=user.id,
        concept_id=c_strong.id,
        attempts=3,
        correct=3,
        mastery_score=0.9,
    )
    cm_weak = ConceptMastery(
        user_id=user.id,
        concept_id=c_weak.id,
        attempts=2,
        correct=1,
        mastery_score=0.5,
    )
    cm_zero = ConceptMastery(
        user_id=user.id,
        concept_id=c_zero.id,
        attempts=0,  # <-- should be excluded
        correct=0,
        mastery_score=0.0,
    )
    cm_budget = ConceptMastery(
        user_id=user.id,
        concept_id=c_budget.id,
        attempts=1,
        correct=1,
        mastery_score=1.0,
    )
    db_session.add_all([cm_strong, cm_weak, cm_zero, cm_budget])
    await db_session.flush()

    return user, {
        "c_strong": c_strong,
        "c_weak": c_weak,
        "c_zero": c_zero,
        "c_budget": c_budget,
    }


async def test_concepts_attached_to_correct_topic(db_session, strengths_user_with_concepts):
    """TopicStrength for 'savings' has two attempted concepts, not the zero-attempts one."""
    user, concepts = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    savings_topics = [t for t in result.topics if t.topic == "savings"]
    assert len(savings_topics) == 1
    savings = savings_topics[0]

    assert len(savings.concepts) == 2
    concept_names = {c.name for c in savings.concepts}
    assert "Compound Interest" in concept_names
    assert "APR" in concept_names
    # zero-attempts concept excluded
    assert "Inflation" not in concept_names


async def test_concept_mastery_score_and_status(db_session, strengths_user_with_concepts):
    """Each ConceptStrength has correct mastery_score, status, and attempts."""
    user, _ = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    savings = next(t for t in result.topics if t.topic == "savings")
    by_name = {c.name: c for c in savings.concepts}

    strong_c = by_name["Compound Interest"]
    assert strong_c.mastery_score == pytest.approx(0.9)
    assert strong_c.status == "strong"
    assert strong_c.attempts == 3

    weak_c = by_name["APR"]
    assert weak_c.mastery_score == pytest.approx(0.5)
    assert weak_c.status == "needs_practice"
    assert weak_c.attempts == 2


async def test_concepts_sorted_needs_practice_first(db_session, strengths_user_with_concepts):
    """Concepts within a topic are needs_practice-first (mirrors topic sort)."""
    user, _ = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    savings = next(t for t in result.topics if t.topic == "savings")
    statuses = [c.status for c in savings.concepts]
    assert statuses[0] == "needs_practice"
    assert statuses[1] == "strong"


async def test_concept_has_slug_and_concept_id(db_session, strengths_user_with_concepts):
    """Each ConceptStrength carries slug and concept_id UUID."""
    user, concepts = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    savings = next(t for t in result.topics if t.topic == "savings")
    by_name = {c.name: c for c in savings.concepts}

    strong_c = by_name["Compound Interest"]
    assert strong_c.concept_id == concepts["c_strong"].id
    assert strong_c.slug == concepts["c_strong"].slug


async def test_zero_attempts_concept_excluded(db_session, strengths_user_with_concepts):
    """A ConceptMastery row with attempts=0 must NOT appear in any topic's concepts."""
    user, concepts = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    all_concept_ids = {c.concept_id for t in result.topics for c in t.concepts}
    assert concepts["c_zero"].id not in all_concept_ids


async def test_topic_with_no_attempted_concepts_is_empty_list(db_session):
    """A topic with a TopicMastery row but no ConceptMastery rows gets concepts=[]."""
    from app.models.skill_profile import TopicMastery
    from app.models.user import User

    uid = uuid.uuid4().hex[:8]
    user = User(
        email=f"noconcepts_{uid}@example.com",
        username=f"nckid_{uid}",
        password_hash="x",
        dob=date(2013, 5, 5),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        TopicMastery(
            user_id=user.id,
            topic="crypto",
            mastery_score=0.6,
            quizzes_attempted=3,
            quizzes_correct=2,
        )
    )
    await db_session.flush()

    result = await get_strengths_and_gaps(db_session, user.id)
    crypto_topics = [t for t in result.topics if t.topic == "crypto"]
    assert len(crypto_topics) == 1
    assert crypto_topics[0].concepts == []


async def test_existing_topic_level_fields_unchanged(db_session, strengths_user_with_concepts):
    """Adding concepts is additive — existing topic-level fields are intact."""
    user, _ = strengths_user_with_concepts
    result = await get_strengths_and_gaps(db_session, user.id)

    savings = next(t for t in result.topics if t.topic == "savings")
    # All pre-Task-3 fields still present
    assert savings.topic == "savings"
    assert savings.mastery_score == pytest.approx(0.7)
    assert savings.status in ("strong", "needs_practice", "new")
    assert isinstance(savings.weak_count, int)
    assert isinstance(savings.due_for_review, int)
    assert isinstance(savings.total_concepts, int)
