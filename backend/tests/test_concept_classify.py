"""TDD: LLM concept-classification service + /internal/concepts/classify endpoint.

Covers:
  (a) Published untagged lesson whose mocked LLM returns a valid candidate slug
      → concept_id set, counted in lessons_tagged.
  (b) Mocked LLM returns a slug not in the taxonomy (hallucination)
      → concept_id stays NULL, counted in lessons_unmatched.
  (c) Mocked LLM abstains (null/empty) → NULL, lessons_unmatched.
  (d) Already-tagged lesson excluded from query + concept_id untouched on re-run.
  (e) Unpublished-module lesson NOT processed (published-only scope).
  (f) limit bounds the count processed.
  (g) Endpoint: no-secret POST → 401/503 (NOT 403 — proves CSRF exemption);
      correct secret → 200 with counts.
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.seed.concepts import seed_concepts
from app.services.concept_classify_service import classify_untagged_lessons

pytestmark = pytest.mark.asyncio(loop_scope="session")

_CLASSIFY_PATH = "/internal/concepts/classify"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _seed(db_session) -> None:
    """Seed the concept taxonomy (idempotent within the test transaction)."""
    await seed_concepts(db_session)
    await db_session.flush()


async def _make_module(
    db_session, *, topic: str = "savings", published: bool = True
) -> Module:
    module = Module(
        topic=topic,
        title="Test Classify Module",
        country_codes=[],
        is_premium=False,
        order_index=0,
        published=published,
    )
    db_session.add(module)
    await db_session.flush()
    return module


async def _make_lesson(
    db_session,
    *,
    module: Module,
    question: str = "What is compound interest?",
    concept_id: uuid.UUID | None = None,
) -> Lesson:
    lesson = Lesson(
        module_id=module.id,
        type="quiz",
        content_json={"question": question, "choices": ["A", "B"], "answer_index": 0, "explanation": "x"},
        xp_reward=10,
        order_index=0,
        concept_id=concept_id,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


def _mock_llm(slug_response: str | None) -> AsyncMock:
    """Return a mock LLM client whose complete() returns the given slug as JSON."""
    mock_client = AsyncMock()
    payload = json.dumps({"concept_slug": slug_response})
    mock_client.complete = AsyncMock(return_value=payload)
    return mock_client


# ── service unit tests ─────────────────────────────────────────────────────────


async def test_valid_slug_sets_concept_id(db_session):
    """LLM returns a valid taxonomy slug → concept_id is set, counted as tagged."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    lesson = await _make_lesson(db_session, module=module)
    assert lesson.concept_id is None

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is not None, "valid slug must set concept_id"
    concept = await db_session.get(Concept, lesson.concept_id)
    assert concept is not None
    assert concept.slug == "compound-interest"
    assert result["lessons_tagged"] >= 1
    assert result["lessons_seen"] >= 1


async def test_hallucinated_slug_leaves_null(db_session):
    """LLM returns a slug not in the taxonomy → concept_id stays NULL, unmatched."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    lesson = await _make_lesson(db_session, module=module, question="Hallucinated concept?")

    mock_client = _mock_llm("totally-invented-slug-xyz-9999")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is None, "hallucinated slug must leave concept_id NULL"
    assert result["lessons_unmatched"] >= 1


async def test_abstain_null_leaves_null(db_session):
    """LLM returns null → concept_id stays NULL, counted as unmatched."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    lesson = await _make_lesson(db_session, module=module, question="Abstain lesson?")

    mock_client = _mock_llm(None)
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is None, "abstain (null) must leave concept_id NULL"
    assert result["lessons_unmatched"] >= 1


async def test_already_tagged_excluded_idempotent(db_session):
    """Already-tagged lesson excluded from query; second run does not overwrite it."""
    await _seed(db_session)
    existing_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest", Concept.topic == "savings")
    )
    assert existing_concept is not None

    module = await _make_module(db_session, topic="savings")
    lesson = await _make_lesson(
        db_session, module=module, question="Pre-tagged lesson?", concept_id=existing_concept.id
    )

    # Even if the LLM would return a different slug, the already-tagged row must
    # not be touched.
    mock_client = _mock_llm("simple-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id == existing_concept.id, (
        "already-tagged concept_id must not be overwritten"
    )


async def test_unpublished_module_lesson_not_processed(db_session):
    """Lesson under an unpublished module must not be classified."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings", published=False)
    lesson = await _make_lesson(db_session, module=module, question="Unpublished lesson?")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is None, "lesson under unpublished module must be skipped"


async def test_limit_bounds_processed_count(db_session):
    """limit parameter caps the number of lessons processed."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    # Create 5 untagged lessons
    for i in range(5):
        await _make_lesson(db_session, module=module, question=f"Limit test lesson {i}?")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=2)

    assert result["lessons_seen"] <= 2, "limit must cap lessons_seen"


# ── endpoint auth + CSRF tests ─────────────────────────────────────────────────


async def test_classify_endpoint_503_when_cron_secret_unset(client, monkeypatch):
    """503 when CRON_SECRET is not configured."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_CLASSIFY_PATH, headers={"X-Cron-Secret": "anything"})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_classify_endpoint_401_when_secret_missing(client, monkeypatch):
    """401 when no X-Cron-Secret header is sent."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_CLASSIFY_PATH)
    assert r.status_code == 401


async def test_classify_endpoint_401_when_secret_wrong(client, monkeypatch):
    """401 when an incorrect secret is sent."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_CLASSIFY_PATH, headers={"X-Cron-Secret": "wrong"})
    assert r.status_code == 401


async def test_classify_endpoint_200_correct_secret(client, db_session, monkeypatch):
    """200 with counts returned when the correct secret is provided."""
    await _seed(db_session)
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        r = await client.post(_CLASSIFY_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert "lessons_seen" in body
    assert "lessons_tagged" in body
    assert "lessons_unmatched" in body
    assert "lessons_errored" in body


async def test_classify_endpoint_csrf_exempt_returns_not_403(client, monkeypatch):
    """The endpoint is CSRF-exempt: no CSRF token/cookie returns 401/503, NOT 403.

    This guards the known gotcha where forgetting to add a path to
    _DEFAULT_EXEMPT_PATHS in csrf.py causes GitHub Actions cron POSTs to 403.
    """
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    # No Origin, no X-CSRF-Token, no csrf_token cookie — a cron caller's request.
    r = await client.post(_CLASSIFY_PATH)
    assert r.status_code != 403, (
        f"Expected 401 or 503 (CSRF-exempt), got 403 — "
        f"did you forget to add {_CLASSIFY_PATH!r} to _DEFAULT_EXEMPT_PATHS in core/csrf.py?"
    )
    assert r.status_code in (401, 503)
