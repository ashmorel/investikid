"""Per-market isolation tests for the Revise feeders.

Ensures that weak-concept due counts, record_weak_concept upserts, and
reinforce_concept updates are all scoped to the active market so that
concepts in market GB are invisible when the user's active market is US,
and a wrong answer in US creates/increments a US row (not the GB row).
"""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content import Lesson, LessonCompletion, Module
from app.models.skill_profile import SpacedRepetitionItem, WeakConcept
from app.models.user import User
from app.services.revise_service import build_session
from app.services.skill_profile_service import record_weak_concept, reinforce_concept
from app.services.spaced_repetition_service import (
    get_due_count,
    get_due_items,
    get_next_due_at,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_user_with_market(db_session, *, email: str, active_market: str) -> User:
    """Create a user whose active_market_code is `active_market`."""
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash="x",
        dob=datetime(2012, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        active_market_code=active_market,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _add_wc_with_sr(
    db_session,
    *,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
    market_code: str,
    days_overdue: int = 1,
) -> WeakConcept:
    """Add an unresolved WeakConcept with a due SR item."""
    wc = WeakConcept(
        user_id=user_id,
        topic=topic,
        concept=concept,
        resolved=False,
        market_code=market_code,
    )
    db_session.add(wc)
    await db_session.flush()
    db_session.add(
        SpacedRepetitionItem(
            user_id=user_id,
            weak_concept_id=wc.id,
            ease_factor=2.5,
            interval_days=1,
            repetition_count=0,
            next_review_at=datetime.now(UTC) - timedelta(days=days_overdue),
        )
    )
    await db_session.flush()
    return wc


# ---------------------------------------------------------------------------
# Test 1: GB weak-concepts do NOT leak into US due count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_gb_weak_concepts_invisible_in_us_due_count(db_session):
    """A user with GB weak-concepts switched to US active market sees 0 US due items."""
    user = await _seed_user_with_market(db_session, email="iso1@example.com", active_market="US")

    # Seed two GB weak-concepts with overdue SR items
    await _add_wc_with_sr(db_session, user_id=user.id, topic="stocks", concept="GB concept A",
                          market_code="GB")
    await _add_wc_with_sr(db_session, user_id=user.id, topic="saving", concept="GB concept B",
                          market_code="GB")

    # Active market is US — neither GB concept should count
    count_us = await get_due_count(db_session, user.id, market_code="US")
    assert count_us == 0, "GB concepts must not appear in US due count"

    # Sanity: they ARE visible when queried as GB
    count_gb = await get_due_count(db_session, user.id, market_code="GB")
    assert count_gb == 2


# ---------------------------------------------------------------------------
# Test 2: get_due_items returns no items for wrong market
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_get_due_items_market_filtered(db_session):
    user = await _seed_user_with_market(db_session, email="iso2@example.com", active_market="US")

    await _add_wc_with_sr(db_session, user_id=user.id, topic="stocks", concept="GB only concept",
                          market_code="GB")

    due_us = await get_due_items(db_session, user.id, market_code="US")
    assert due_us == []

    due_gb = await get_due_items(db_session, user.id, market_code="GB")
    assert len(due_gb) == 1


# ---------------------------------------------------------------------------
# Test 3: get_next_due_at ignores other-market items
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_get_next_due_at_market_filtered(db_session):
    user = await _seed_user_with_market(db_session, email="iso3@example.com", active_market="US")

    await _add_wc_with_sr(db_session, user_id=user.id, topic="stocks", concept="GB next due",
                          market_code="GB")

    next_at_us = await get_next_due_at(db_session, user.id, market_code="US")
    assert next_at_us is None  # no US items exist

    next_at_gb = await get_next_due_at(db_session, user.id, market_code="GB")
    assert next_at_gb is not None


# ---------------------------------------------------------------------------
# Test 4: US wrong answer creates a US row, not incrementing the GB row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_us_wrong_answer_creates_us_row_not_gb(db_session):
    """record_weak_concept with market_code='US' must not touch the GB row."""
    user = await _seed_user_with_market(db_session, email="iso4@example.com", active_market="US")

    # Pre-existing GB weak concept with times_wrong=1
    gb_wc = WeakConcept(
        user_id=user.id, topic="stocks", concept="Shared concept",
        resolved=False, market_code="GB", times_wrong=1,
    )
    db_session.add(gb_wc)
    await db_session.flush()
    gb_id = gb_wc.id

    # Simulate a wrong answer in the US market
    await record_weak_concept(db_session, user.id, "stocks", "Shared concept", market_code="US")
    await db_session.flush()

    # The GB row must be unchanged
    gb_row = await db_session.get(WeakConcept, gb_id)
    assert gb_row is not None
    assert gb_row.times_wrong == 1, "GB row must not be incremented by a US wrong answer"

    # A NEW US row must have been created
    us_row = await db_session.scalar(
        select(WeakConcept).where(
            WeakConcept.user_id == user.id,
            WeakConcept.topic == "stocks",
            WeakConcept.concept == "Shared concept",
            WeakConcept.market_code == "US",
        )
    )
    assert us_row is not None, "US wrong answer must create a US weak-concept row"
    assert us_row.times_wrong == 1


# ---------------------------------------------------------------------------
# Test 5: reinforce_concept with US market only updates the US row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio(loop_scope="session")
async def test_reinforce_concept_market_scoped(db_session):
    """reinforce_concept(market_code='US') must not update the GB row."""
    user = await _seed_user_with_market(db_session, email="iso5@example.com", active_market="US")

    gb_wc = WeakConcept(
        user_id=user.id, topic="saving", concept="Budget concept",
        resolved=False, market_code="GB", times_reinforced=0,
    )
    us_wc = WeakConcept(
        user_id=user.id, topic="saving", concept="Budget concept",
        resolved=False, market_code="US", times_reinforced=0,
    )
    db_session.add(gb_wc)
    db_session.add(us_wc)
    await db_session.flush()
    gb_id = gb_wc.id
    us_id = us_wc.id

    await reinforce_concept(db_session, user.id, "saving", "Budget concept", market_code="US")
    await db_session.flush()

    gb_refreshed = await db_session.get(WeakConcept, gb_id)
    us_refreshed = await db_session.get(WeakConcept, us_id)

    assert gb_refreshed.times_reinforced == 0, "GB row must not be touched by US reinforce"
    assert us_refreshed.times_reinforced == 1, "US row must be incremented"


# ---------------------------------------------------------------------------
# Test 6: Scheduled refresher in US must NOT suppress a GB refresher
# ---------------------------------------------------------------------------

def _quiz_payload(q):
    return {"question": q, "choices": ["a", "b", "c"], "answer_index": 1,
            "explanation": "because", "variant_rung": "core"}


@pytest.mark.asyncio(loop_scope="session")
async def test_us_scheduled_refresher_does_not_suppress_gb_refresher(db_session):
    """A concept with a future SR review in market US must not suppress the same
    concept offered as a refresher when the user's active market is GB."""
    # User whose active market is GB
    user = await _seed_user_with_market(
        db_session, email="iso6@example.com", active_market="GB"
    )

    # Create a module + lesson for the shared concept
    module = Module(
        topic="investing", title="Investing", country_codes=[],
        is_premium=False, order_index=0, icon="📊",
    )
    db_session.add(module)
    await db_session.flush()

    concept = "What is compound interest?"
    lesson = Lesson(
        module_id=module.id, type="quiz", xp_reward=10, order_index=0,
        content_json={"question": concept, "choices": ["a", "b"], "answer_index": 0},
    )
    db_session.add(lesson)
    await db_session.flush()

    # The user has completed this lesson (makes it eligible as a GB refresher)
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id))

    # A WeakConcept row for market US with a FUTURE SR review (concept recently
    # revised in US → should NOT suppress GB refresher after the fix)
    us_wc = WeakConcept(
        user_id=user.id, topic="investing", concept=concept,
        resolved=True, market_code="US",
    )
    db_session.add(us_wc)
    await db_session.flush()
    db_session.add(SpacedRepetitionItem(
        user_id=user.id, weak_concept_id=us_wc.id, ease_factor=2.5,
        interval_days=3, repetition_count=1,
        next_review_at=datetime.now(UTC) + timedelta(days=3),  # future → would suppress
    ))
    await db_session.flush()

    mock_quiz = AsyncMock(side_effect=lambda *a, **k: _quiz_payload(k["concept"]))
    with patch("app.services.revise_service.generate_practice_quiz", mock_quiz):
        items = await build_session(db_session, user, module_id=None)

    # The concept has a scheduled SR item in US, but the user's active market is GB.
    # It must be offered as a GB refresher (not suppressed).
    refresher_concepts = [i["concept"] for i in items if i["kind"] == "refresher"]
    assert concept in refresher_concepts, (
        "A US-scheduled refresher must not suppress the same concept as a GB refresher"
    )
