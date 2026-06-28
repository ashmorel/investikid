"""TDD: concept backfill service + /internal/concepts/backfill endpoint.

Covers:
  (a) WeakConcept/Lesson whose text matches a seeded concept gets concept_id set.
  (b) Unmatchable rows stay NULL.
  (c) Re-running is idempotent — already-set rows are not changed, NULL rows
      that still don't match stay NULL.
  (d) Endpoint rejects unauthenticated / wrong-secret calls (401/503, NOT 403).
  (e) The endpoint is CSRF-exempt (not 403 without CSRF header or cookie).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.concept import Concept
from app.models.content import Lesson, Module
from app.models.skill_profile import WeakConcept
from app.seed.concepts import seed_concepts
from app.services.concept_backfill_service import run_backfill

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/concepts/backfill"


# ── helpers ───────────────────────────────────────────────────────────────────


async def _seed(db_session):
    """Seed the concept taxonomy once (idempotent within the test transaction)."""
    await seed_concepts(db_session)
    await db_session.flush()


async def _make_module(db_session, *, topic: str = "savings", published: bool = True) -> Module:
    module = Module(
        topic=topic,
        title="Test Module",
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
    title: str,
    concept_id: uuid.UUID | None = None,
) -> Lesson:
    lesson = Lesson(
        module_id=module.id,
        type="card",
        content_json={"title": title, "body": "Test body."},
        xp_reward=10,
        order_index=0,
        concept_id=concept_id,
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def _make_weak_concept(
    db_session,
    *,
    user_id: uuid.UUID,
    topic: str,
    concept: str,
    concept_id: uuid.UUID | None = None,
) -> WeakConcept:
    wc = WeakConcept(
        user_id=user_id,
        topic=topic,
        concept=concept,
        concept_id=concept_id,
    )
    db_session.add(wc)
    await db_session.flush()
    return wc


async def _make_user(db_session) -> uuid.UUID:
    """Insert a minimal user row and return its id."""
    from datetime import date

    from app.models.user import User

    user = User(
        email=f"backfill-test-{uuid.uuid4().hex[:8]}@example.com",
        username=f"bfuser{uuid.uuid4().hex[:6]}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    return user.id


# ── service unit tests ────────────────────────────────────────────────────────


async def test_weak_concept_matched_text_sets_concept_id(db_session):
    """A WeakConcept whose .concept text matches a seeded concept gets concept_id."""
    await _seed(db_session)
    user_id = await _make_user(db_session)

    wc = await _make_weak_concept(
        db_session,
        user_id=user_id,
        topic="savings",
        concept="compound interest",  # normalises to compound-interest
    )
    assert wc.concept_id is None

    result = await run_backfill(db_session)

    await db_session.refresh(wc)
    assert wc.concept_id is not None, "matched WeakConcept should have concept_id set"

    concept = await db_session.get(Concept, wc.concept_id)
    assert concept is not None
    assert concept.slug == "compound-interest"

    assert result["weak_concepts_matched"] >= 1
    assert result["weak_concepts_total"] >= 1


async def test_weak_concept_unmatched_stays_null(db_session):
    """An unmatchable WeakConcept keeps concept_id = NULL after backfill."""
    await _seed(db_session)
    user_id = await _make_user(db_session)

    wc = await _make_weak_concept(
        db_session,
        user_id=user_id,
        topic="savings",
        concept="totally-made-up-concept-xyz-999",
    )

    result = await run_backfill(db_session)

    await db_session.refresh(wc)
    assert wc.concept_id is None, "unmatched WeakConcept must stay NULL"
    assert result["weak_concepts_total"] >= 1


async def test_weak_concept_already_set_not_changed(db_session):
    """A WeakConcept already tagged with a concept_id is left untouched."""
    await _seed(db_session)
    user_id = await _make_user(db_session)

    # Find a real concept to pre-assign.
    existing_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest", Concept.topic == "savings")
    )
    assert existing_concept is not None

    wc = await _make_weak_concept(
        db_session,
        user_id=user_id,
        topic="savings",
        concept="some other text",
        concept_id=existing_concept.id,  # already tagged
    )

    result = await run_backfill(db_session)

    await db_session.refresh(wc)
    # Must still be the same concept we set — backfill only touches NULL rows.
    assert wc.concept_id == existing_concept.id
    # The already-set row must NOT appear in wc_total (query filters concept_id IS NULL).
    # We can't assert exact count (other tests may add rows), but matched <= total.
    assert result["weak_concepts_matched"] <= result["weak_concepts_total"]


async def test_lesson_matched_title_sets_concept_id(db_session):
    """A published Lesson whose content_json title matches a concept gets concept_id."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings", published=True)
    lesson = await _make_lesson(
        db_session, module=module, title="Compound Interest"
    )
    assert lesson.concept_id is None

    result = await run_backfill(db_session)

    await db_session.refresh(lesson)
    assert lesson.concept_id is not None, "matched Lesson should have concept_id set"
    assert result["lessons_matched"] >= 1
    assert result["lessons_total"] >= 1


async def test_lesson_unmatched_stays_null(db_session):
    """A published Lesson with no matching concept keeps concept_id = NULL."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings", published=True)
    lesson = await _make_lesson(
        db_session, module=module, title="Totally Unknown Gibberish XYZ 9999"
    )

    result = await run_backfill(db_session)

    await db_session.refresh(lesson)
    assert lesson.concept_id is None
    assert result["lessons_total"] >= 1


async def test_lesson_already_set_not_touched(db_session):
    """A Lesson already tagged with concept_id is excluded from the backfill query."""
    await _seed(db_session)
    existing_concept = await db_session.scalar(
        select(Concept).where(Concept.slug == "compound-interest", Concept.topic == "savings")
    )
    assert existing_concept is not None

    module = await _make_module(db_session, topic="savings", published=True)
    lesson = await _make_lesson(
        db_session, module=module, title="Some title", concept_id=existing_concept.id
    )

    await run_backfill(db_session)

    await db_session.refresh(lesson)
    assert lesson.concept_id == existing_concept.id


async def test_backfill_idempotent_rerun_changes_nothing(db_session):
    """Running the backfill twice produces the same result; second run touches nothing."""
    await _seed(db_session)
    user_id = await _make_user(db_session)
    module = await _make_module(db_session, topic="savings", published=True)

    # One matchable WeakConcept and one matchable Lesson.
    wc = await _make_weak_concept(
        db_session, user_id=user_id, topic="savings", concept="compound interest"
    )
    lesson = await _make_lesson(db_session, module=module, title="Compound Interest")

    # First run.
    await run_backfill(db_session)
    await db_session.refresh(wc)
    await db_session.refresh(lesson)
    cid_wc_after_first = wc.concept_id
    cid_lesson_after_first = lesson.concept_id
    assert cid_wc_after_first is not None
    assert cid_lesson_after_first is not None

    # Second run — already-set rows are excluded from the query entirely.
    r2 = await run_backfill(db_session)
    await db_session.refresh(wc)
    await db_session.refresh(lesson)

    assert wc.concept_id == cid_wc_after_first, "second run must not change already-set wc"
    assert lesson.concept_id == cid_lesson_after_first, "second run must not change already-set lesson"

    # On the second run, neither of these two rows appears in the NULL query.
    # (Other tests run in the same session may still produce NULL rows, so we
    # can only assert that our specific rows didn't regress.)
    assert r2["weak_concepts_matched"] <= r2["weak_concepts_total"]
    assert r2["lessons_matched"] <= r2["lessons_total"]


# ── endpoint auth tests ───────────────────────────────────────────────────────


async def test_endpoint_503_when_cron_secret_unset(client, monkeypatch):
    """503 when CRON_SECRET is not configured."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "anything"})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_endpoint_401_when_secret_missing(client, monkeypatch):
    """401 when no X-Cron-Secret header is sent."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_PATH)
    assert r.status_code == 401


async def test_endpoint_401_when_secret_wrong(client, monkeypatch):
    """401 when an incorrect secret is sent."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "wrong"})
    assert r.status_code == 401


async def test_endpoint_200_with_correct_secret(client, db_session, monkeypatch):
    """200 with counts returned when the correct secret is provided."""
    await _seed(db_session)
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    body = r.json()
    assert "weak_concepts_total" in body
    assert "weak_concepts_matched" in body
    assert "lessons_total" in body
    assert "lessons_matched" in body


async def test_endpoint_csrf_exempt_returns_not_403(client, monkeypatch):
    """The endpoint is CSRF-exempt: sending no CSRF token/cookie returns 401/503, NOT 403.

    This guards the known gotcha where forgetting to add a path to
    _DEFAULT_EXEMPT_PATHS in csrf.py causes GitHub Actions cron POSTs to 403.
    """
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    # No Origin, no X-CSRF-Token, no csrf_token cookie — a cron caller's request.
    r = await client.post(_PATH)
    assert r.status_code != 403, (
        f"Expected 401 or 503 (CSRF-exempt), got 403 — "
        f"did you forget to add {_PATH!r} to _DEFAULT_EXEMPT_PATHS in core/csrf.py?"
    )
    assert r.status_code in (401, 503)
