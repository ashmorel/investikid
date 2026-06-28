"""TDD: concept taxonomy seed — idempotent, covers all 9 topics, valid tiers."""
from collections import defaultdict

import pytest
from sqlalchemy import func, select

from app.models.concept import Concept
from app.seed.concepts import CONCEPTS, seed_concepts

pytestmark = pytest.mark.asyncio(loop_scope="session")

_TOPICS = {
    "stocks",
    "savings",
    "real_estate",
    "budgeting",
    "risk",
    "crypto",
    "taxes",
    "debt",
    "entrepreneurship",
}


async def test_seed_idempotent(db_session):
    """Running the seed twice must not create duplicate rows."""
    await seed_concepts(db_session)
    await db_session.flush()
    first = await db_session.scalar(select(func.count()).select_from(Concept))

    await seed_concepts(db_session)
    await db_session.flush()
    second = await db_session.scalar(select(func.count()).select_from(Concept))

    assert first == second, f"Row count changed on second run: {first} -> {second}"


async def test_each_topic_has_at_least_three_concepts(db_session):
    """Every topic must have ≥3 concepts."""
    await seed_concepts(db_session)
    await db_session.flush()
    rows = (await db_session.scalars(select(Concept))).all()

    by_topic: dict[str, int] = defaultdict(int)
    for row in rows:
        by_topic[row.topic] += 1

    for topic in _TOPICS:
        count = by_topic.get(topic, 0)
        assert count >= 3, f"Topic '{topic}' only has {count} concept(s); need ≥3"


async def test_all_difficulty_tiers_present(db_session):
    """All three tiers (1, 2, 3) must be represented across the taxonomy."""
    await seed_concepts(db_session)
    await db_session.flush()
    rows = (await db_session.scalars(select(Concept))).all()
    tiers = {row.difficulty_tier for row in rows}
    assert tiers == {1, 2, 3}, f"Expected tiers {{1,2,3}}, got {tiers}"


async def test_difficulty_tier_values_are_valid(db_session):
    """Every concept must have difficulty_tier ∈ {1, 2, 3}."""
    await seed_concepts(db_session)
    await db_session.flush()
    rows = (await db_session.scalars(select(Concept))).all()
    bad = [r.slug for r in rows if r.difficulty_tier not in {1, 2, 3}]
    assert not bad, f"Invalid difficulty_tier on: {bad}"


async def test_all_slugs_unique(db_session):
    """No duplicate slugs anywhere."""
    await seed_concepts(db_session)
    await db_session.flush()
    rows = (await db_session.scalars(select(Concept))).all()
    slugs = [r.slug for r in rows]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs found"


async def test_topics_are_from_allowed_set(db_session):
    """Every concept.topic must be one of the 9 canonical topics."""
    await seed_concepts(db_session)
    await db_session.flush()
    rows = (await db_session.scalars(select(Concept))).all()
    bad_topics = {r.topic for r in rows} - _TOPICS
    assert not bad_topics, f"Concepts with unknown topics: {bad_topics}"


async def test_catalog_constant_completeness():
    """The CONCEPTS constant itself covers all 9 topics with ≥3 each (no DB needed)."""
    by_topic: dict[str, int] = defaultdict(int)
    for c in CONCEPTS:
        by_topic[c["topic"]] += 1

    for topic in _TOPICS:
        count = by_topic.get(topic, 0)
        assert count >= 3, f"CONCEPTS list: topic '{topic}' has only {count} (need ≥3)"

    slugs = [c["slug"] for c in CONCEPTS]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs in CONCEPTS list"

    bad_tiers = [c["slug"] for c in CONCEPTS if c["difficulty_tier"] not in {1, 2, 3}]
    assert not bad_tiers, f"Invalid tiers in CONCEPTS: {bad_tiers}"
