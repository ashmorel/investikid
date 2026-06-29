"""
Task 1 – DiagnosticItem model TDD.

Asserts:
- A DiagnosticItem can be created and persisted.
- Defaults: status="draft", times_shown=0, times_correct=0.
- Nullable fields: concept_id, approved_by, approved_at default None.
- All three status values (draft/approved/retired) persist correctly.
- choices round-trips a JSON list.
"""

import uuid

import pytest

from app.models.diagnostic import DiagnosticItem

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(**kwargs) -> DiagnosticItem:
    defaults = dict(
        market_code="GB",
        topic="stocks",
        difficulty_tier=1,
        question="What is a share?",
        choices=["A piece of a company", "A type of bond", "A savings account", "A loan"],
        answer_index=0,
        explanation="A share represents partial ownership of a company.",
        source="authored",
    )
    defaults.update(kwargs)
    return DiagnosticItem(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_diagnostic_item_can_be_created(db_session):
    item = _item()
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched is not None
    assert fetched.market_code == "GB"
    assert fetched.topic == "stocks"
    assert fetched.difficulty_tier == 1
    assert fetched.question == "What is a share?"
    assert fetched.answer_index == 0
    assert fetched.source == "authored"


async def test_diagnostic_item_defaults(db_session):
    item = _item(market_code="US", topic="savings")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.status == "draft"
    assert fetched.times_shown == 0
    assert fetched.times_correct == 0
    assert fetched.created_at is not None


async def test_diagnostic_item_nullable_fields_default_none(db_session):
    item = _item(market_code="CA", topic="budgeting")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.concept_id is None
    assert fetched.approved_by is None
    assert fetched.approved_at is None


async def test_diagnostic_item_status_draft(db_session):
    item = _item(market_code="AU", topic="risk", status="draft")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.status == "draft"


async def test_diagnostic_item_status_approved(db_session):
    item = _item(market_code="SG", topic="crypto", status="approved")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.status == "approved"


async def test_diagnostic_item_status_retired(db_session):
    item = _item(market_code="HK", topic="taxes", status="retired")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.status == "retired"


async def test_diagnostic_item_choices_round_trips(db_session):
    choices = ["Option A", "Option B", "Option C", "Option D"]
    item = _item(market_code="GB", topic="debt", choices=choices)
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.choices == choices


async def test_diagnostic_item_concept_id_can_be_set(db_session):
    from app.models.concept import Concept

    concept = Concept(
        topic="stocks",
        slug="diag-test-what-is-share",
        name="What is a share?",
        difficulty_tier=1,
        order_index=99,
    )
    db_session.add(concept)
    await db_session.flush()

    item = _item(market_code="GB", topic="stocks", concept_id=concept.id)
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.concept_id == concept.id


async def test_diagnostic_item_approved_fields_can_be_set(db_session):
    from datetime import UTC, datetime

    approver_id = uuid.uuid4()
    approved_at = datetime.now(UTC)
    item = _item(
        market_code="GB",
        topic="entrepreneurship",
        status="approved",
        approved_by=approver_id,
        approved_at=approved_at,
    )
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.approved_by == approver_id
    assert fetched.approved_at is not None


async def test_verifier_fields_default_none(db_session):
    """New DiagnosticItem has all four verifier fields defaulting to None."""
    item = _item(market_code="GB", topic="investing")
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.verifier_status is None
    assert fetched.verifier_answer_index is None
    assert fetched.verifier_note is None
    assert fetched.verified_at is None


async def test_verifier_fields_persist_when_set(db_session):
    """Verifier fields round-trip through the DB correctly."""
    from datetime import UTC, datetime

    verified_at = datetime.now(UTC)
    item = _item(
        market_code="US",
        topic="savings",
        verifier_status="mismatch",
        verifier_answer_index=2,
        verifier_note="The verifier disagrees with the authored answer.",
        verified_at=verified_at,
    )
    db_session.add(item)
    await db_session.flush()
    fetched = await db_session.get(DiagnosticItem, item.id)
    assert fetched.verifier_status == "mismatch"
    assert fetched.verifier_answer_index == 2
    assert fetched.verifier_note == "The verifier disagrees with the authored answer."
    assert fetched.verified_at is not None
