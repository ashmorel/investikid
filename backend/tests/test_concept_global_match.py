"""TDD A1.2 Task 1 — global slug matching for classify / generate / approve / reset.

Covers:
  (1) resolve_slug_global: seeded slug from any topic → its UUID; unknown → None.
  (2) classify: a lesson whose module.topic is a free-form non-taxonomy string
      (e.g. "growing-your-money") with a valid mocked LLM pick → concept_id set
      (NOT skipped). This is the core regression for the bug: the old code skipped
      all such lessons because _fetch_concepts_for_topic returned empty.
  (3) approval: a draft with a valid concept_slug under a free-form module topic
      → concept_id resolved globally (not topic-scoped), set on the Lesson.
  (4) generator: generate_native_level_lessons passes FULL taxonomy slugs (not
      topic-scoped) into the generation prompt.
  (5) /internal/concepts/classify/reset:
        - no-secret → 401 or 503 (NOT 403 — proves CSRF exempt).
        - correct secret → nulls only untagged rows; tagged rows untouched.
        - returns {"reset": <count>}.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.concept import Concept
from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.seed.concepts import seed_concepts
from app.services.concept_classify_service import classify_untagged_lessons
from app.services.concept_mapper import resolve_slug_global
from app.services.lesson_approval_service import approve_level_drafts

pytestmark = pytest.mark.asyncio(loop_scope="session")

_RESET_PATH = "/internal/concepts/classify/reset"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _seed(db_session) -> None:
    await seed_concepts(db_session)
    await db_session.flush()


async def _make_module(db_session, *, topic: str, published: bool = True) -> Module:
    module = Module(
        topic=topic,
        title=f"Test Module ({topic})",
        country_codes=[],
        is_premium=False,
        order_index=0,
        published=published,
    )
    db_session.add(module)
    await db_session.flush()
    return module


async def _make_level(db_session, *, topic: str = "growing-your-money") -> tuple[Module, Level]:
    module = await _make_module(db_session, topic=topic)
    level = Level(
        module_id=module.id, title="L1", order_index=1,
        is_premium=False, pass_threshold=0.7,
    )
    db_session.add(level)
    await db_session.flush()
    return module, level


async def _make_lesson(
    db_session,
    *,
    module: Module,
    question: str = "What is compound interest?",
    concept_id: uuid.UUID | None = None,
    concept_classified_at=None,
    content_json: dict | None = None,
) -> Lesson:
    if content_json is None:
        content_json = {
            "question": question,
            "choices": ["A", "B"],
            "answer_index": 0,
            "explanation": "x",
        }
    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        content_json=content_json,
        xp_reward=10,
        order_index=0,
        concept_id=concept_id,
        concept_classified_at=concept_classified_at,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


def _mock_llm(slug_response: str | None) -> AsyncMock:
    mock_client = AsyncMock()
    payload = json.dumps({"concept_slug": slug_response})
    mock_client.complete = AsyncMock(return_value=payload)
    return mock_client


# ── (1) resolve_slug_global ────────────────────────────────────────────────────


async def test_resolve_slug_global_returns_id_for_any_topic(db_session):
    """A seeded slug from any topic resolves to its UUID globally (no topic arg needed)."""
    await _seed(db_session)
    # "compound-interest" is in topic "savings"
    savings_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest")
    )
    assert savings_concept is not None, "compound-interest must be seeded"
    result = await resolve_slug_global(db_session, "compound-interest")
    assert result == savings_concept.id

    # "what-is-a-stock" is in topic "stocks"
    stocks_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "what-is-a-stock")
    )
    assert stocks_concept is not None, "what-is-a-stock must be seeded"
    result2 = await resolve_slug_global(db_session, "what-is-a-stock")
    assert result2 == stocks_concept.id


async def test_resolve_slug_global_normalized_variant(db_session):
    """Normalized variants (spaces, underscores, mixed case) still resolve."""
    await _seed(db_session)
    concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest")
    )
    assert concept is not None
    r1 = await resolve_slug_global(db_session, "compound interest")
    assert r1 == concept.id, "space-separated form must resolve globally"
    r2 = await resolve_slug_global(db_session, "Compound_Interest")
    assert r2 == concept.id, "underscore/mixed-case form must resolve globally"


async def test_resolve_slug_global_unknown_returns_none(db_session):
    """An unknown slug returns None — the model can never invent a concept."""
    await _seed(db_session)
    result = await resolve_slug_global(db_session, "totally-invented-slug-xyz-9999")
    assert result is None


async def test_resolve_slug_global_none_input_returns_none(db_session):
    """None or empty string inputs return None without error."""
    await _seed(db_session)
    assert await resolve_slug_global(db_session, None) is None
    assert await resolve_slug_global(db_session, "") is None


# ── (2) classify: free-form topic regression test ─────────────────────────────


async def test_classify_free_form_topic_not_skipped(db_session):
    """Core regression: a lesson whose module.topic is NOT in the 9-topic taxonomy
    (e.g. 'growing-your-money') must NOT be skipped — with a full-taxonomy candidate
    list the LLM can still pick a valid slug and concept_id must be set.
    """
    await _seed(db_session)
    # "growing-your-money" is not one of the 9 canonical topics — it's a free-form
    # slug produced by the regenerated curriculum.
    module = await _make_module(db_session, topic="growing-your-money")
    lesson = await _make_lesson(db_session, module=module, question="How does money grow over time?")
    assert lesson.concept_id is None
    assert lesson.concept_classified_at is None

    # LLM picks "compound-interest" which exists in the global taxonomy (topic=savings).
    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is not None, (
        "free-form topic lesson must NOT be skipped — concept_id must be set"
    )
    concept = await db_session.get(Concept, lesson.concept_id)
    assert concept is not None
    assert concept.slug == "compound-interest"
    assert lesson.concept_classified_at is not None
    assert result["lessons_tagged"] >= 1
    # Must NOT appear in skipped
    assert result["lessons_skipped"] == 0 or result["lessons_tagged"] >= 1


async def test_classify_uses_full_taxonomy_not_topic_scoped(db_session):
    """The classifier must call the LLM (not skip) for a free-form topic lesson,
    proving the full taxonomy is passed rather than an empty topic-scoped list.
    """
    await _seed(db_session)
    module = await _make_module(db_session, topic="money-management-basics")
    lesson = await _make_lesson(
        db_session, module=module, question="What does it mean to budget your money?"
    )

    mock_client = _mock_llm("budgeting-basics")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    # The LLM must have been called (not pre-skipped). If the lesson was skipped,
    # mock_client.complete would have zero calls for this lesson's text.
    # We verify this by checking the lesson got processed (tagged or unmatched).
    await db_session.refresh(lesson)
    assert lesson.concept_classified_at is not None
    # Even if "budgeting-basics" doesn't exist, the lesson should be unmatched not skipped.
    assert result["lessons_skipped"] == 0


# ── (3) approval: free-form topic → global resolve ────────────────────────────


async def test_approve_draft_free_form_topic_sets_concept_id(db_session):
    """A draft whose module.topic is free-form but whose concept_slug is valid in the
    global taxonomy → concept_id resolved and set on the approved Lesson.
    """
    await _seed(db_session)
    module, level = await _make_level(db_session, topic="growing-your-money")

    draft = LessonDraft(
        level_id=level.id, type="card",
        content_json={"title": "Compound Interest", "body": "Money grows."},
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
    assert lesson.concept_id is not None, (
        "concept_id must be set even when module.topic is a free-form string"
    )
    concept = await db_session.get(Concept, lesson.concept_id)
    assert concept is not None
    assert concept.slug == "compound-interest"


# ── (4) generator: full taxonomy slugs ────────────────────────────────────────


async def test_generator_passes_full_taxonomy_slugs(db_session):
    """generate_native_level_lessons must pass the FULL taxonomy slug list (not
    topic-scoped) as concept_slugs to the generation prompt.
    """
    await _seed(db_session)
    # Module with a free-form topic — no topic-scoped concepts exist.
    module, level = await _make_level(db_session, topic="growing-your-money")

    brief_mock = AsyncMock()
    brief_mock.brief_json = {"market": "GB", "currency": "GBP"}

    card_json = json.dumps({"title": "Saving Goals", "body": "Save for what matters."})
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=card_json)

    captured_calls: list[dict] = []

    async def capturing_generate_one(session, *, level, module, concept, lesson_type,
                                      brief=None, source_text=None, complexity_tier=None,
                                      avoid=None, concept_slugs=None):
        captured_calls.append({"concept_slugs": concept_slugs})
        # Return a minimal draft so the loop doesn't crash.
        from app.models.lesson_draft import LessonDraft as LD
        draft = LD(
            level_id=level.id, type=lesson_type,
            content_json={"title": "x", "body": "y"},
            concept=concept, model_used="test",
            moderation_safe=True, moderation_category=None,
            concept_slug=None,
        )
        session.add(draft)
        await session.flush()
        return draft

    with patch(
        "app.services.admin_content_generation_service._generate_one",
        side_effect=capturing_generate_one,
    ):
        from app.services.admin_content_generation_service import generate_native_level_lessons
        await generate_native_level_lessons(
            db_session, level,
            brief=brief_mock,
            concepts=["compound interest"],
        )

    assert captured_calls, "generation must have been called at least once"
    # The slug list passed in must include concepts from other topics (not just
    # 'growing-your-money' which has none in the taxonomy).
    slugs = captured_calls[0]["concept_slugs"]
    assert slugs is not None, "concept_slugs must be passed to _generate_one"
    assert len(slugs) > 0, "concept_slugs must be non-empty (full taxonomy)"
    # Spot-check: compound-interest (savings topic) must be in the list.
    assert "compound-interest" in slugs, (
        f"full-taxonomy slugs must include cross-topic entries; got {slugs[:5]}…"
    )
    # what-is-a-stock (stocks topic) must also be present.
    assert "what-is-a-stock" in slugs, (
        "full-taxonomy slugs must include entries from all topics"
    )


# ── (5) /internal/concepts/classify/reset ─────────────────────────────────────


async def test_reset_csrf_exempt_no_secret_not_403(client, monkeypatch):
    """No CSRF token, no secret → 401 or 503 (NOT 403) — proves CSRF exemption."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_RESET_PATH)
    assert r.status_code != 403, (
        f"Expected 401 or 503 (CSRF-exempt), got 403 — "
        f"add {_RESET_PATH!r} to _DEFAULT_EXEMPT_PATHS in core/csrf.py"
    )
    assert r.status_code in (401, 503)


async def test_reset_503_when_cron_secret_unset(client, monkeypatch):
    """503 when CRON_SECRET is not configured."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_RESET_PATH, headers={"X-Cron-Secret": "anything"})
    assert r.status_code == 503


async def test_reset_401_wrong_secret(client, monkeypatch):
    """401 when the wrong secret is sent."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_RESET_PATH, headers={"X-Cron-Secret": "wrong"})
    assert r.status_code == 401


async def test_reset_nulls_only_untagged_rows(client, db_session, monkeypatch):
    """With the correct secret: only rows where concept_id IS NULL have
    concept_classified_at reset to NULL.  Rows that already have concept_id set
    are never touched (tagged lesson invariant).
    """
    from datetime import UTC, datetime
    await _seed(db_session)

    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    # Find a real concept to tag with.
    tagged_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest")
    )
    assert tagged_concept is not None

    stamped_at = datetime.now(UTC)

    # Row A: stamped AND tagged (concept_id set) — must NOT be reset.
    module_a = await _make_module(db_session, topic="savings")
    lesson_tagged = await _make_lesson(
        db_session, module=module_a, question="Tagged lesson — must stay",
        concept_id=tagged_concept.id,
        concept_classified_at=stamped_at,
    )

    # Row B: stamped but NOT tagged (concept_id NULL) — must be reset.
    module_b = await _make_module(db_session, topic="growing-your-money")
    lesson_untagged = await _make_lesson(
        db_session, module=module_b, question="Untagged stamped lesson — must be reset",
        concept_id=None,
        concept_classified_at=stamped_at,
    )

    await db_session.flush()

    r = await client.post(_RESET_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert "reset" in body, f"response must contain 'reset' key; got {body}"
    assert body["reset"] >= 1, "at least the untagged row must be counted"

    await db_session.refresh(lesson_tagged)
    await db_session.refresh(lesson_untagged)

    # Tagged row: untouched.
    assert lesson_tagged.concept_classified_at is not None, (
        "tagged lesson's concept_classified_at must NOT be nulled"
    )
    assert lesson_tagged.concept_id is not None, (
        "tagged lesson's concept_id must NOT be cleared"
    )

    # Untagged row: concept_classified_at reset.
    assert lesson_untagged.concept_classified_at is None, (
        "untagged lesson's concept_classified_at must be reset to NULL"
    )
    assert lesson_untagged.concept_id is None, (
        "concept_id must remain NULL on the reset row"
    )
