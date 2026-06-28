"""
Task 1 – Concept model TDD.

Asserts:
- A Concept can be created and persisted.
- slug uniqueness is enforced at the DB level.
- Lesson.concept_id and WeakConcept.concept_id accept None (nullable FK) and
  can also be set to a real Concept row.
- WeakConcept.concept (free-text) is untouched.
"""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.models.skill_profile import WeakConcept
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _concept(**kwargs) -> Concept:
    defaults = dict(
        topic="stocks",
        slug="stocks-what-is-a-share",
        name="What is a share?",
        difficulty_tier=1,
        order_index=1,
    )
    defaults.update(kwargs)
    return Concept(**defaults)


async def _module(db_session) -> Module:
    m = Module(topic="stocks", title="Stocks 101", country_codes=["GB"], order_index=0)
    db_session.add(m)
    await db_session.flush()
    return m


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_concept_can_be_created(db_session):
    c = _concept()
    db_session.add(c)
    await db_session.flush()
    fetched = await db_session.get(Concept, c.id)
    assert fetched is not None
    assert fetched.slug == "stocks-what-is-a-share"
    assert fetched.topic == "stocks"
    assert fetched.difficulty_tier == 1
    assert fetched.blurb is None
    assert fetched.created_at is not None


async def test_concept_blurb_optional(db_session):
    c = _concept(slug="stocks-dividends", name="Dividends", blurb="A share of profit.")
    db_session.add(c)
    await db_session.flush()
    fetched = await db_session.get(Concept, c.id)
    assert fetched.blurb == "A share of profit."


async def test_concept_slug_unique(db_session):
    c1 = _concept(slug="stocks-unique-slug", name="C1")
    c2 = _concept(slug="stocks-unique-slug", name="C2")
    db_session.add(c1)
    await db_session.flush()
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lesson_concept_id_defaults_none(db_session):
    m = await _module(db_session)
    lesson = Lesson(module_id=m.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.flush()
    fetched = await db_session.get(Lesson, lesson.id)
    assert fetched.concept_id is None


async def test_lesson_concept_id_can_be_set(db_session):
    c = _concept(slug="stocks-lesson-link", name="Link concept")
    db_session.add(c)
    await db_session.flush()

    m = await _module(db_session)
    lesson = Lesson(
        module_id=m.id,
        type="card",
        content_json={},
        xp_reward=10,
        order_index=0,
        concept_id=c.id,
    )
    db_session.add(lesson)
    await db_session.flush()
    fetched = await db_session.get(Lesson, lesson.id)
    assert fetched.concept_id == c.id


async def test_weak_concept_concept_id_defaults_none(db_session):
    user = User(
        email="wc_null@x.com",
        username="wc_null",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    wc = WeakConcept(
        user_id=user.id,
        topic="stocks",
        concept="price-to-earnings ratio",
    )
    db_session.add(wc)
    await db_session.flush()
    fetched = await db_session.get(WeakConcept, wc.id)
    assert fetched.concept_id is None
    # free-text field untouched
    assert fetched.concept == "price-to-earnings ratio"


async def test_weak_concept_concept_id_can_be_set(db_session):
    c = _concept(slug="stocks-wc-link", name="WC link concept")
    db_session.add(c)
    await db_session.flush()

    user = User(
        email="wc_set@x.com",
        username="wc_set",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    wc = WeakConcept(
        user_id=user.id,
        topic="stocks",
        concept="some free text",
        concept_id=c.id,
    )
    db_session.add(wc)
    await db_session.flush()
    fetched = await db_session.get(WeakConcept, wc.id)
    assert fetched.concept_id == c.id
    assert fetched.concept == "some free text"
