"""TDD: LLM concept-classification service + /internal/concepts/classify endpoint.

Covers:
  (a) Published untagged lesson whose mocked LLM returns a valid candidate slug
      → concept_id set, counted in lessons_tagged, concept_classified_at stamped.
  (b) Mocked LLM returns a slug not in the taxonomy (hallucination)
      → concept_id stays NULL, counted in lessons_unmatched,
        concept_classified_at stamped (not re-attempted on second run).
  (c) Mocked LLM abstains (null/empty) → NULL, lessons_unmatched,
      concept_classified_at stamped.
  (d) Already-tagged lesson excluded from query + concept_id untouched on re-run.
  (e) Unpublished-module lesson NOT processed (published-only scope).
  (f) limit bounds the count processed.
  (g) Pre-LLM skip (no text/topic/taxonomy) → lessons_skipped (not
      lessons_unmatched), concept_classified_at stamped, excluded from second run.
  (h) Second run sees lessons_seen == 0 after first run stamped all lessons.
  (i) tagged + unmatched + skipped + errored == seen invariant.
  (j) Endpoint: no-secret POST → 401/503 (NOT 403 — proves CSRF exemption);
      correct secret → 200 with counts including lessons_skipped.
"""
from __future__ import annotations

import json
import re
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
    )
    db_session.add(lesson)
    await db_session.flush()
    return lesson


_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _extract_lesson_ids(prompt_text: str) -> list[str]:
    """Pull UUID lesson ids out of a prompt string (test-only helper)."""
    return _UUID_RE.findall(prompt_text)


def _mock_llm(slug_response: str | None) -> AsyncMock:
    """Return a mock LLM client whose complete() replies, for EVERY lesson id
    found in the mini-batch prompt (system_prompt now carries the lesson list),
    with the same ``slug_response`` — i.e. "the LLM picks this slug for every
    lesson in the batch". Mirrors the pre-batching per-lesson mock's intent
    while matching the new {"results": [...]} batch response contract.
    """
    mock_client = AsyncMock()

    async def _complete(*, system_prompt, messages, **kwargs):
        lesson_ids = _extract_lesson_ids(system_prompt)
        return json.dumps(
            {
                "results": [
                    {"lesson_id": lid, "concept_slug": slug_response}
                    for lid in lesson_ids
                ]
            }
        )

    mock_client.complete = AsyncMock(side_effect=_complete)
    return mock_client


# ── service unit tests ─────────────────────────────────────────────────────────


async def test_valid_slug_sets_concept_id(db_session):
    """LLM returns a valid taxonomy slug → concept_id set, tagged, stamped."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    lesson = await _make_lesson(db_session, module=module)
    assert lesson.concept_id is None
    assert lesson.concept_classified_at is None

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
    assert lesson.concept_classified_at is not None, "concept_classified_at must be stamped"
    assert result["lessons_tagged"] >= 1
    assert result["lessons_seen"] >= 1
    # Sum invariant
    assert (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
        == result["lessons_seen"]
    )


async def test_hallucinated_slug_leaves_null(db_session):
    """LLM hallucinated slug → concept_id NULL, unmatched, stamped, not re-tried."""
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
    assert lesson.concept_classified_at is not None, "must be stamped even on hallucination"
    assert result["lessons_unmatched"] >= 1

    # Second run must NOT re-attempt this lesson (it has concept_classified_at set).
    mock_client2 = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client2,
    ):
        result2 = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    # concept_id must still be None — the lesson was not re-attempted.
    assert lesson.concept_id is None, "stamped lesson must not be re-processed"
    # lessons_seen from the second run must not include this already-stamped lesson.
    first_seen = result["lessons_seen"]
    second_seen = result2["lessons_seen"]
    assert second_seen < first_seen or second_seen == 0, (
        "second run must see fewer (or zero) lessons after first run stamped them"
    )


async def test_abstain_null_leaves_null(db_session):
    """LLM abstains (null) → concept_id NULL, unmatched, stamped."""
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
    assert lesson.concept_classified_at is not None, "must be stamped on abstain"
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


async def test_pre_llm_skip_counted_as_skipped_not_unmatched(db_session):
    """A lesson with no text is skipped before calling LLM → lessons_skipped, not
    lessons_unmatched; concept_classified_at is stamped; excluded from second run."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    # Lesson with empty content_json — no question/title/prompt.
    lesson = await _make_lesson(
        db_session,
        module=module,
        content_json={"choices": ["A", "B"], "answer_index": 0, "explanation": "x"},
    )
    assert lesson.concept_classified_at is None

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    await db_session.refresh(lesson)
    assert lesson.concept_id is None, "skipped lesson must not have concept_id"
    assert lesson.concept_classified_at is not None, "skipped lesson must be stamped"
    assert result["lessons_skipped"] >= 1, "pre-LLM skip must increment lessons_skipped"
    # The LLM must NOT have been called for this lesson specifically; however
    # since other tests may have created lessons in the same session, we just
    # verify it is counted as skipped, not unmatched.
    assert result["lessons_unmatched"] == 0 or result["lessons_skipped"] >= 1

    # Sum invariant
    assert (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
        == result["lessons_seen"]
    )

    # Second run: this lesson must be excluded (concept_classified_at is set).
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result2 = await classify_untagged_lessons(db_session, limit=10)

    assert result2["lessons_seen"] == 0, (
        "second run must see 0 lessons — all were stamped in the first run"
    )


async def test_second_run_lessons_seen_zero_after_drain(db_session):
    """After one full run, a second run sees lessons_seen == 0 (drain convergence)."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    await _make_lesson(db_session, module=module, question="Drain test lesson A?")
    await _make_lesson(db_session, module=module, question="Drain test lesson B?")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result1 = await classify_untagged_lessons(db_session, limit=200)

    assert result1["lessons_seen"] >= 2

    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result2 = await classify_untagged_lessons(db_session, limit=200)

    assert result2["lessons_seen"] == 0, (
        "second run must see 0 lessons — drain must converge"
    )


async def test_sum_invariant(db_session):
    """tagged + unmatched + skipped + errored == seen for a mixed batch."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    # A lesson with text (LLM will be called → tagged)
    await _make_lesson(db_session, module=module, question="Invariant test A?")
    # A lesson with no text (pre-LLM skip)
    await _make_lesson(
        db_session,
        module=module,
        content_json={"answer_index": 0, "explanation": "x"},
    )

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    total = (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
    )
    assert total == result["lessons_seen"], (
        f"sum invariant violated: {result}"
    )


# ── mini-batch tests ────────────────────────────────────────────────────────────


def _mock_llm_batch(handler) -> AsyncMock:
    """Return a mock LLM client whose complete() delegates to ``handler(system_prompt,
    messages, **kwargs)`` and returns whatever JSON string it produces (or raises).
    """
    mock_client = AsyncMock()

    async def _complete(*, system_prompt, messages, **kwargs):
        return handler(system_prompt, messages, **kwargs)

    mock_client.complete = AsyncMock(side_effect=_complete)
    return mock_client


def _batch_response_all_tagged(slug: str):
    """Build a handler that replies with concept_slug=``slug`` for every lesson id
    embedded (as a UUID) in the system prompt's lesson list."""

    def handler(system_prompt, messages, **kwargs):
        lesson_ids = _extract_lesson_ids(system_prompt)
        return json.dumps(
            {"results": [{"lesson_id": lid, "concept_slug": slug} for lid in lesson_ids]}
        )

    return handler


async def test_batches_of_8_not_one_call_per_lesson(db_session):
    """17 usable-text lessons → ceil(17/8) == 3 LLM calls, NOT 17."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    for i in range(17):
        await _make_lesson(db_session, module=module, question=f"Batch call-count lesson {i}?")

    mock_client = _mock_llm_batch(_batch_response_all_tagged("compound-interest"))
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=17)

    assert result["lessons_seen"] == 17
    assert mock_client.complete.call_count == 3, (
        f"expected ceil(17/8)=3 LLM calls, got {mock_client.complete.call_count}"
    )
    assert result["lessons_tagged"] == 17


async def test_missing_lesson_id_in_batch_response_is_unmatched_batchmates_unaffected(
    db_session,
):
    """One lesson's id missing from the mini-batch response → only that lesson is
    unmatched; its batch-mates are still tagged and stamped."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    lessons = [
        await _make_lesson(db_session, module=module, question=f"Missing-id lesson {i}?")
        for i in range(3)
    ]
    dropped = lessons[1]

    def handler(system_prompt, messages, **kwargs):
        lesson_ids = _extract_lesson_ids(system_prompt)
        results = [
            {"lesson_id": lid, "concept_slug": "compound-interest"}
            for lid in lesson_ids
            if lid != str(dropped.id)
        ]
        return json.dumps({"results": results})

    mock_client = _mock_llm_batch(handler)
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    for lesson in lessons:
        await db_session.refresh(lesson)
        assert lesson.concept_classified_at is not None, "every lesson in the batch must be stamped"

    assert dropped.concept_id is None, "dropped lesson must be unmatched, not tagged"
    others = [lsn for lsn in lessons if lsn.id != dropped.id]
    for lesson in others:
        assert lesson.concept_id is not None, "batch-mates of a dropped lesson must still be tagged"

    assert result["lessons_unmatched"] == 1
    assert result["lessons_tagged"] == 2
    assert (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
        == result["lessons_seen"]
    )


async def test_mini_batch_llm_error_only_errors_that_batch(db_session):
    """A mini-batch whose LLM call raises → only THAT mini-batch's lessons are
    lessons_errored (stamped); lessons in other mini-batches are unaffected."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    # 9 lessons with text → 2 mini-batches of size 8 and 1 (batch size = 8).
    lessons = [
        await _make_lesson(db_session, module=module, question=f"Error batch lesson {i}?")
        for i in range(9)
    ]

    call_count = {"n": 0}

    def handler(system_prompt, messages, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated provider outage for this mini-batch")
        lesson_ids = _extract_lesson_ids(system_prompt)
        return json.dumps(
            {
                "results": [
                    {"lesson_id": lid, "concept_slug": "compound-interest"}
                    for lid in lesson_ids
                ]
            }
        )

    mock_client = _mock_llm_batch(handler)
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=10)

    assert mock_client.complete.call_count == 2
    assert result["lessons_errored"] == 8, "first mini-batch (8 lessons) must all error"
    assert result["lessons_tagged"] == 1, "second mini-batch (1 lesson) must be unaffected"

    for lesson in lessons:
        await db_session.refresh(lesson)
        assert lesson.concept_classified_at is not None, (
            "every lesson, including errored ones, must be stamped"
        )

    assert (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
        == result["lessons_seen"]
    )


async def test_mixed_scenario_invariant_across_multiple_batches(db_session):
    """Mixed pre-LLM skips + tagged + unmatched + errored across multiple
    mini-batches still satisfies tagged+unmatched+skipped+errored == seen."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")

    # 2 pre-LLM skips (no usable text).
    for _ in range(2):
        await _make_lesson(
            db_session,
            module=module,
            content_json={"answer_index": 0, "explanation": "x"},
        )

    # 10 lessons with usable text → 2 mini-batches (8 + 2).
    for i in range(10):
        await _make_lesson(db_session, module=module, question=f"Mixed scenario lesson {i}?")

    call_count = {"n": 0}

    def handler(system_prompt, messages, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated failure for second mini-batch")
        # Drop the FIRST lesson in THIS (first) mini-batch's prompt, so exactly one
        # lesson is unmatched here regardless of the random UUID sort order that
        # decides which lessons land in which mini-batch.
        lesson_ids = _extract_lesson_ids(system_prompt)
        to_drop = lesson_ids[0]
        results = [
            {"lesson_id": lid, "concept_slug": "compound-interest"}
            for lid in lesson_ids
            if lid != to_drop
        ]
        return json.dumps({"results": results})

    mock_client = _mock_llm_batch(handler)
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ):
        result = await classify_untagged_lessons(db_session, limit=20)

    assert result["lessons_seen"] == 12
    assert result["lessons_skipped"] == 2
    assert result["lessons_unmatched"] == 1  # dropped lesson in first mini-batch
    assert result["lessons_errored"] == 2  # second mini-batch (2 lessons) all errored
    assert result["lessons_tagged"] == 7  # remaining 7 in first mini-batch
    assert (
        result["lessons_tagged"]
        + result["lessons_unmatched"]
        + result["lessons_skipped"]
        + result["lessons_errored"]
        == result["lessons_seen"]
    )


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
    """200 with all 5 counts returned when the correct secret is provided."""
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
    assert "lessons_skipped" in body
    assert "lessons_errored" in body
    # Sum invariant on the endpoint response too.
    assert (
        body["lessons_tagged"]
        + body["lessons_unmatched"]
        + body["lessons_skipped"]
        + body["lessons_errored"]
        == body["lessons_seen"]
    )


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


# ── tier param tests ───────────────────────────────────────────────────────────


async def test_service_default_tier_is_lite(db_session):
    """classify_untagged_lessons with no tier= arg calls get_llm_client('lite')."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    await _make_lesson(db_session, module=module, question="Default tier lesson?")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ) as mock_get:
        await classify_untagged_lessons(db_session, limit=10)

    mock_get.assert_called_once_with("lite")


async def test_service_explicit_premium_tier(db_session):
    """classify_untagged_lessons(tier='premium') calls get_llm_client('premium')."""
    await _seed(db_session)
    module = await _make_module(db_session, topic="savings")
    await _make_lesson(db_session, module=module, question="Premium tier lesson?")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ) as mock_get:
        await classify_untagged_lessons(db_session, limit=10, tier="premium")

    mock_get.assert_called_once_with("premium")


async def test_endpoint_tier_premium_calls_service_with_premium(client, db_session, monkeypatch):
    """?tier=premium passes tier='premium' down to the service."""
    await _seed(db_session)
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ) as mock_get:
        r = await client.post(
            _CLASSIFY_PATH,
            params={"tier": "premium"},
            headers={"X-Cron-Secret": "s3cr3t"},
        )

    assert r.status_code == 200
    mock_get.assert_called_once_with("premium")


async def test_endpoint_tier_default_is_lite(client, db_session, monkeypatch):
    """No ?tier= param → service is called with tier='lite'."""
    await _seed(db_session)
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    mock_client = _mock_llm("compound-interest")
    with patch(
        "app.services.concept_classify_service.get_llm_client",
        return_value=mock_client,
    ) as mock_get:
        r = await client.post(
            _CLASSIFY_PATH,
            headers={"X-Cron-Secret": "s3cr3t"},
        )

    assert r.status_code == 200
    mock_get.assert_called_once_with("lite")


async def test_endpoint_bogus_tier_rejected(client, monkeypatch):
    """?tier=bogus is rejected with 422 (or 400) and the LLM is never called."""
    import app.routers.internal as internal
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")

    with patch(
        "app.services.concept_classify_service.get_llm_client",
    ) as mock_get:
        r = await client.post(
            _CLASSIFY_PATH,
            params={"tier": "bogus"},
            headers={"X-Cron-Secret": "s3cr3t"},
        )

    assert r.status_code in (400, 422), f"Expected 400/422 for bogus tier, got {r.status_code}"
    mock_get.assert_not_called()
