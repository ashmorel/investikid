"""TDD: concept mapper — resolve_concept_slug and integration with lesson approval."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.concept import Concept
from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.seed.concepts import seed_concepts
from app.services.concept_mapper import resolve_concept_slug
from app.services.lesson_approval_service import approve_level_drafts
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ── helpers ───────────────────────────────────────────────────────────────────

async def _seed(db_session):
    """Seed concept taxonomy into the test DB."""
    await seed_concepts(db_session)
    await db_session.flush()


async def _make_level(db_session, *, topic: str = "savings") -> tuple[Module, Level]:
    module = Module(
        topic=topic, title="Test Module", country_codes=[], is_premium=False,
        order_index=0, min_age=10, max_age=16,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="Level 1", order_index=1,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return module, level


# ── concept_mapper unit tests ─────────────────────────────────────────────────

async def test_exact_slug_resolves(db_session):
    """An exact slug match within the correct topic returns the concept id."""
    await _seed(db_session)
    concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest", Concept.topic == "savings")
    )
    assert concept is not None, "compound-interest concept must exist in savings"
    result = await resolve_concept_slug(db_session, "compound-interest", "savings")
    assert result == concept.id


async def test_normalized_variant_resolves(db_session):
    """'compound interest' and 'Compound_Interest' normalize to 'compound-interest'."""
    await _seed(db_session)
    concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest", Concept.topic == "savings")
    )
    assert concept is not None

    # Spaced variant (matches on normalized name "compound interest → compound-interest")
    r1 = await resolve_concept_slug(db_session, "compound interest", "savings")
    assert r1 == concept.id, "space-separated form should resolve"

    # Underscore + mixed-case variant
    r2 = await resolve_concept_slug(db_session, "Compound_Interest", "savings")
    assert r2 == concept.id, "underscore/mixed-case form should resolve"


async def test_nonsense_slug_returns_none(db_session):
    """A slug that doesn't match anything returns None."""
    await _seed(db_session)
    result = await resolve_concept_slug(db_session, "totally-made-up-nonsense-xyz", "savings")
    assert result is None


async def test_wrong_topic_returns_none(db_session):
    """A valid slug from a different topic returns None (topic scoping)."""
    await _seed(db_session)
    # 'compound-interest' exists in 'savings', not in 'stocks'
    result = await resolve_concept_slug(db_session, "compound-interest", "stocks")
    assert result is None


async def test_none_slug_returns_none(db_session):
    """A None or empty slug returns None without error."""
    await _seed(db_session)
    assert await resolve_concept_slug(db_session, None, "savings") is None
    assert await resolve_concept_slug(db_session, "", "savings") is None


# ── approval integration tests ────────────────────────────────────────────────

CARD_JSON = {"title": "Compound Interest", "body": "Money grows on money."}


async def test_approved_draft_with_known_slug_sets_concept_id(db_session):
    """A draft whose concept_slug maps to a real concept gets concept_id set on the Lesson."""
    await _seed(db_session)
    _, level = await _make_level(db_session, topic="savings")

    # Insert a draft with concept_slug="compound-interest" (valid for savings topic).
    draft = LessonDraft(
        level_id=level.id, type="card", content_json=CARD_JSON,
        concept="compound interest", model_used="test-model",
        moderation_safe=True, moderation_category=None,
        concept_slug="compound-interest",
    )
    db_session.add(draft)
    await db_session.flush()

    result = await approve_level_drafts(db_session, level, replace=False)
    assert result["approved"] == 1

    lesson = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).first()
    assert lesson is not None
    assert lesson.concept_id is not None, "concept_id should be set from a valid slug"

    # Verify it points to the right concept.
    concept = await db_session.get(Concept, lesson.concept_id)
    assert concept is not None
    assert concept.slug == "compound-interest"


async def test_approved_draft_with_unknown_slug_persists_with_null_concept_id(db_session, caplog):
    """A draft with an unrecognised concept_slug persists with concept_id=NULL and logs."""
    await _seed(db_session)
    _, level = await _make_level(db_session, topic="savings")

    draft = LessonDraft(
        level_id=level.id, type="card", content_json=CARD_JSON,
        concept="some weird concept", model_used="test-model",
        moderation_safe=True, moderation_category=None,
        concept_slug="totally-unknown-slug",
    )
    db_session.add(draft)
    await db_session.flush()

    import logging
    with caplog.at_level(logging.INFO, logger="app.services.lesson_approval_service"):
        result = await approve_level_drafts(db_session, level, replace=False)

    assert result["approved"] == 1

    lesson = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).first()
    assert lesson is not None
    assert lesson.concept_id is None, "concept_id should be NULL for an unmapped slug"

    # Confirm the structured log line was emitted.
    assert any(
        "concept_unmapped" in r.message and "totally-unknown-slug" in r.message
        for r in caplog.records
    ), f"Expected concept_unmapped log; got: {[r.message for r in caplog.records]}"


async def test_approved_draft_without_slug_persists_with_null_concept_id(db_session):
    """A draft with no concept_slug at all persists with concept_id=NULL (no error)."""
    await _seed(db_session)
    _, level = await _make_level(db_session, topic="savings")

    draft = LessonDraft(
        level_id=level.id, type="card", content_json=CARD_JSON,
        concept="some concept", model_used="test-model",
        moderation_safe=True, moderation_category=None,
        concept_slug=None,
    )
    db_session.add(draft)
    await db_session.flush()

    result = await approve_level_drafts(db_session, level, replace=False)
    assert result["approved"] == 1

    lesson = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).first()
    assert lesson is not None
    assert lesson.concept_id is None


async def test_generate_one_with_recognised_slug_sets_concept_slug_on_draft(db_session):
    """When _generate_one produces a JSON with concept_slug, it's stored on the draft."""
    await _seed(db_session)
    module, level = await _make_level(db_session, topic="savings")

    # LLM returns a card with concept_slug included in the JSON.
    llm_response = json.dumps({
        "title": "Saving Goals",
        "body": "Setting a goal helps you save more money.",
        "concept_slug": "compound-interest",
    })

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=llm_response)

    with (
        patch("app.services.admin_content_generation_service.get_llm_client",
              return_value=mock_client),
        patch("app.services.admin_content_generation_service.moderate_output",
              AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))),
    ):
        from app.services.admin_content_generation_service import _generate_one
        draft = await _generate_one(
            db_session, level=level, module=module, concept="compound interest",
            lesson_type="card",
        )

    assert draft is not None
    assert draft.concept_slug == "compound-interest"
    # concept_slug must NOT be stored inside content_json (it was popped out).
    assert "concept_slug" not in draft.content_json


async def test_generate_one_with_unrecognised_slug_stored_for_later_resolution(db_session):
    """A LLM-emitted slug that won't map still gets stored on the draft (mapper logs at approval)."""
    module, level = await _make_level(db_session, topic="stocks")

    llm_response = json.dumps({
        "title": "Stocks Intro",
        "body": "Stocks let you own a piece of a company.",
        "concept_slug": "invented-slug-that-does-not-exist",
    })

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=llm_response)

    with (
        patch("app.services.admin_content_generation_service.get_llm_client",
              return_value=mock_client),
        patch("app.services.admin_content_generation_service.moderate_output",
              AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))),
    ):
        from app.services.admin_content_generation_service import _generate_one
        draft = await _generate_one(
            db_session, level=level, module=module, concept="stocks",
            lesson_type="card",
        )

    assert draft is not None
    assert draft.concept_slug == "invented-slug-that-does-not-exist"
    assert "concept_slug" not in draft.content_json
