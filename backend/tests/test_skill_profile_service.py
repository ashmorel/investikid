import pytest

from app.models.skill_profile import TopicMastery, WeakConcept
from app.services.skill_profile_service import (
    get_mastery_profile,
    record_weak_concept,
    reinforce_concept,
    update_mastery_on_completion,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_update_mastery_correct(db_session, user_with_module):
    user, module, quiz, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=True)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 1
    assert mastery.quizzes_correct == 1
    assert mastery.mastery_score == 1.0


async def test_update_mastery_wrong(db_session, user_with_module):
    user, module, quiz, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=False)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 1
    assert mastery.quizzes_correct == 0
    assert mastery.mastery_score == 0.0


async def test_update_mastery_card_only_updates_activity(db_session, user_with_module):
    user, module, _, card = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=False, correct=None)
    await db_session.flush()

    mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    assert mastery is not None
    assert mastery.quizzes_attempted == 0
    assert mastery.last_activity_at is not None


async def test_record_weak_concept(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc is not None
    assert wc.times_wrong == 1
    assert wc.resolved is False


async def test_record_weak_concept_increments(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc.times_wrong == 2


async def test_reinforce_concept_resolves(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await reinforce_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await reinforce_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    from sqlalchemy import select
    wc = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.concept == "50/30/20 rule",
        )
    )
    assert wc.times_reinforced == 2
    assert wc.resolved is True


async def test_get_mastery_profile(db_session, user_with_module):
    user, _, _, _ = user_with_module
    await update_mastery_on_completion(db_session, user.id, "budgeting", is_quiz=True, correct=True)
    await record_weak_concept(db_session, user.id, "budgeting", "50/30/20 rule")
    await db_session.flush()

    profile = await get_mastery_profile(db_session, user.id)
    assert len(profile["topics"]) == 1
    assert profile["topics"][0]["topic"] == "budgeting"
    assert profile["topics"][0]["mastery_score"] == 1.0
    assert len(profile["weak_concepts"]) == 1
    assert profile["weak_concepts"][0]["concept"] == "50/30/20 rule"
