"""TDD tests for ConceptMastery model + record_concept_attempt service."""

import uuid
from datetime import date

import pytest
import pytest_asyncio

from app.services.skill_profile_service import record_concept_attempt

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture
async def concept_user_and_concept(db_session):
    """Create a bare User and a Concept for concept-mastery tests."""
    from app.models.concept import Concept
    from app.models.user import User

    user = User(
        email=f"cm_{uuid.uuid4().hex[:8]}@example.com",
        username=f"cmkid_{uuid.uuid4().hex[:6]}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)

    concept = Concept(
        topic="budgeting",
        slug=f"slug_{uuid.uuid4().hex[:8]}",
        name="50/30/20 rule",
        difficulty_tier=1,
        order_index=0,
    )
    db_session.add(concept)
    await db_session.flush()
    return user, concept


async def test_first_correct_attempt_creates_row(db_session, concept_user_and_concept):
    """First correct attempt → row with attempts=1, correct=1, score=1.0, last_attempt_at set."""
    from app.models.skill_profile import ConceptMastery

    user, concept = concept_user_and_concept
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await db_session.flush()

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row is not None
    assert row.attempts == 1
    assert row.correct == 1
    assert row.mastery_score == 1.0
    assert row.last_attempt_at is not None


async def test_second_correct_attempt_increments(db_session, concept_user_and_concept):
    """Second correct attempt → attempts=2, correct=2, score=1.0."""
    from app.models.skill_profile import ConceptMastery

    user, concept = concept_user_and_concept
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await db_session.flush()

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row.attempts == 2
    assert row.correct == 2
    assert row.mastery_score == 1.0


async def test_wrong_attempt_lowers_score(db_session, concept_user_and_concept):
    """After 2 correct + 1 wrong → attempts=3, correct=2, score≈0.667."""
    from app.models.skill_profile import ConceptMastery

    user, concept = concept_user_and_concept
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await record_concept_attempt(db_session, user.id, concept.id, correct=False)
    await db_session.flush()

    row = await db_session.get(ConceptMastery, (user.id, concept.id))
    assert row.attempts == 3
    assert row.correct == 2
    assert abs(row.mastery_score - 2 / 3) < 1e-9


async def test_different_user_concept_pair_is_separate_row(db_session, concept_user_and_concept):
    """A different (user, concept) pair gets its own independent row."""
    from app.models.concept import Concept
    from app.models.skill_profile import ConceptMastery
    from app.models.user import User

    user, concept = concept_user_and_concept

    other_user = User(
        email=f"cm2_{uuid.uuid4().hex[:8]}@example.com",
        username=f"cmkid2_{uuid.uuid4().hex[:6]}",
        password_hash="x",
        dob=date(2013, 3, 3),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(other_user)
    other_concept = Concept(
        topic="investing",
        slug=f"slug2_{uuid.uuid4().hex[:8]}",
        name="Diversification",
        difficulty_tier=2,
        order_index=1,
    )
    db_session.add(other_concept)
    await db_session.flush()

    # Record on the original pair (correct) and the other user/concept pair (wrong)
    await record_concept_attempt(db_session, user.id, concept.id, correct=True)
    await record_concept_attempt(db_session, other_user.id, other_concept.id, correct=False)
    await db_session.flush()

    row1 = await db_session.get(ConceptMastery, (user.id, concept.id))
    row2 = await db_session.get(ConceptMastery, (other_user.id, other_concept.id))

    assert row1 is not None and row1.correct == 1 and row1.mastery_score == 1.0
    assert row2 is not None and row2.correct == 0 and row2.mastery_score == 0.0
