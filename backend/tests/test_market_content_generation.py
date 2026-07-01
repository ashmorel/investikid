import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.services.admin_content_generation_service import generate_market_level_lessons
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

# The mocked premium model always returns this valid card.
US_CARD = json.dumps({"title": "Saving up", "body": "A plan for your dollars."})


def _batched_card_response(lessons) -> str:
    """A JSON array response tagged with each source lesson's id, as the batched
    prompt path expects back (one card per source lesson)."""
    items = [
        {
            "source_lesson_id": str(lesson.id),
            "title": "Saving up",
            "body": "A plan for your dollars.",
        }
        for lesson in lessons
    ]
    return json.dumps(items)


US_BRIEF = {
    "currency": "USD",
    "tax_advantaged_accounts": ["Roth IRA", "529 plan"],
    "regulators": ["SEC", "FINRA"],
    "deposit_protection": "FDIC insures up to $250,000",
    "typical_products": ["savings account"],
    "local_examples": ["allowance in a piggy bank"],
    "notes": "Dollars and cents.",
}


async def _seed_gb_level_with_lesson(db_session):
    module = Module(
        topic="savings", title="GB Saving", country_codes=[], is_premium=False,
        order_index=900, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="GB Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    lesson = Lesson(
        module_id=module.id, level_id=level.id, type="card", xp_reward=0, order_index=0,
        content_json={"title": "ISA savings in pounds",
                      "body": "Put your £ into an ISA with the FCA-regulated bank."},
    )
    db_session.add(lesson)
    await db_session.flush()
    return level, lesson


async def _seed_us_level(db_session):
    module = Module(
        topic="savings", title="US Saving", country_codes=[], is_premium=False,
        order_index=901, icon="💵", market_code="US", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="US Level 1", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    return level


async def test_market_generation_grounds_on_brief_and_gb_source(db_session):
    gb_level, gb_lesson = await _seed_gb_level_with_lesson(db_session)
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_batched_card_response([gb_lesson]))
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    # (a) a LessonDraft is created under us_level
    assert len(result.created) == 1
    drafts = (await db_session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == us_level.id)
    )).all()
    assert len(drafts) == 1

    # (b) the LLM was called with a system prompt containing the brief currency
    #     AND the GB source lesson's text.
    assert mock_client.complete.await_count == 1
    system_prompt = mock_client.complete.await_args.kwargs["system_prompt"]
    assert "USD" in system_prompt
    assert "ISA savings in pounds" in system_prompt


async def test_market_generation_skips_non_generatable_video_lessons(db_session):
    """A GB level can contain a `video` lesson (curated YouTube, not LLM-
    generatable). Market generation must SKIP it, not crash with KeyError."""
    module = Module(
        topic="savings", title="GB Mixed", country_codes=[], is_premium=False,
        order_index=902, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    gb_level = Level(module_id=module.id, title="GB Mixed L1", order_index=0,
                     is_premium=False, pass_threshold=0.7)
    db_session.add(gb_level)
    await db_session.flush()
    card_lesson = Lesson(module_id=module.id, level_id=gb_level.id, type="card",
                         xp_reward=0, order_index=1,
                         content_json={"title": "Saving", "body": "Save your £."})
    db_session.add_all([
        Lesson(module_id=module.id, level_id=gb_level.id, type="video",
               xp_reward=0, order_index=0,
               content_json={"caption": "Watch", "youtube_id": "abc123"}),
        card_lesson,
    ])
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_batched_card_response([card_lesson]))
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    # The video lesson is skipped; only the card is generated (no KeyError).
    assert result.skipped == 1
    assert len(result.created) == 1
    assert mock_client.complete.await_count == 1


async def _seed_gb_level_with_n_lessons(db_session, *, n: int, lesson_type: str = "quiz",
                                        order_index: int = 903):
    """GB level with ``n`` LLM-generatable lessons of the same ``lesson_type``."""
    module = Module(
        topic="savings", title="GB Batch", country_codes=[], is_premium=False,
        order_index=order_index, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="GB Batch Level", order_index=0,
                  is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()
    lessons = []
    for i in range(n):
        if lesson_type == "quiz":
            content = {
                "question": f"Quiz {i} about ISAs in pounds",
                "choices": ["a", "b"],
                "answer_index": 0,
                "explanation": "Because of the FCA.",
            }
        else:
            content = {"title": f"Card {i} ISA savings", "body": "Put your £ into an ISA."}
        lesson = Lesson(
            module_id=module.id, level_id=level.id, type=lesson_type, xp_reward=0,
            order_index=i, content_json=content,
        )
        db_session.add(lesson)
        lessons.append(lesson)
    await db_session.flush()
    return level, lessons


def _batched_quiz_response(lessons) -> str:
    """A JSON array response tagged with each source lesson's id, as the batched
    prompt path expects back."""
    items = [
        {
            "source_lesson_id": str(lesson.id),
            "question": f"Adapted quiz {i}",
            "choices": ["x", "y"],
            "answer_index": 0,
            "explanation": "Adapted explanation.",
        }
        for i, lesson in enumerate(lessons)
    ]
    return json.dumps(items)


async def test_market_generation_batches_same_type_lessons(db_session):
    """12 quiz source lessons of the SAME type → ceil(12/5) = 3 LLM calls, not 12."""
    gb_level, gb_lessons = await _seed_gb_level_with_n_lessons(db_session, n=12, lesson_type="quiz")
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    call_count = 0

    async def fake_complete(*, system_prompt, messages, **kwargs):
        nonlocal call_count
        # Figure out which mini-batch this is from the shrinking pool.
        start = call_count * 5
        batch = gb_lessons[start:start + 5]
        call_count += 1
        return _batched_quiz_response(batch)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=fake_complete)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    assert mock_client.complete.await_count == 3  # ceil(12/5)
    assert len(result.created) == 12
    assert result.skipped == 0
    drafts = (await db_session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == us_level.id)
    )).all()
    assert len(drafts) == 12
    assert all(d.type == "quiz" for d in drafts)


async def test_market_generation_batches_mixed_types_independently(db_session):
    """6 card + 6 quiz source lessons → grouped by type, each batched independently
    (2 LLM calls per type = 4 total, far fewer than 12 lessons)."""
    module = Module(
        topic="savings", title="GB Mixed Types", country_codes=[], is_premium=False,
        order_index=904, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    gb_level = Level(module_id=module.id, title="GB Mixed Types Level", order_index=0,
                     is_premium=False, pass_threshold=0.7)
    db_session.add(gb_level)
    await db_session.flush()

    card_lessons, quiz_lessons = [], []
    for i in range(6):
        card = Lesson(module_id=module.id, level_id=gb_level.id, type="card", xp_reward=0,
                      order_index=i, content_json={"title": f"Card {i}", "body": "Save £."})
        db_session.add(card)
        card_lessons.append(card)
    for i in range(6):
        quiz = Lesson(module_id=module.id, level_id=gb_level.id, type="quiz", xp_reward=0,
                      order_index=6 + i,
                      content_json={"question": f"Q{i}", "choices": ["a", "b"],
                                    "answer_index": 0, "explanation": "Because."})
        db_session.add(quiz)
        quiz_lessons.append(quiz)
    await db_session.flush()

    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    card_calls = {"n": 0}
    quiz_calls = {"n": 0}

    async def fake_complete(*, system_prompt, messages, **kwargs):
        if '"question"' in system_prompt or "quiz" in system_prompt.lower().split("adapt")[0]:
            pass
        # Distinguish by schema hint content in the system prompt.
        if "answer_index" in system_prompt:
            start = quiz_calls["n"] * 5
            batch = quiz_lessons[start:start + 5]
            quiz_calls["n"] += 1
            items = [
                {"source_lesson_id": str(lesson.id), "question": f"Adapted Q{i}",
                 "choices": ["x", "y"], "answer_index": 0, "explanation": "Adapted."}
                for i, lesson in enumerate(batch)
            ]
            return json.dumps(items)
        else:
            start = card_calls["n"] * 5
            batch = card_lessons[start:start + 5]
            card_calls["n"] += 1
            items = [
                {"source_lesson_id": str(lesson.id), "title": f"Adapted card {i}",
                 "body": "Adapted body about dollars."}
                for i, lesson in enumerate(batch)
            ]
            return json.dumps(items)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=fake_complete)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    # 6 cards -> ceil(6/5)=2 calls, 6 quizzes -> ceil(6/5)=2 calls = 4 total.
    assert mock_client.complete.await_count == 4
    assert len(result.created) == 12
    assert result.skipped == 0
    created_types = {d.type for d in result.created}
    assert created_types == {"card", "quiz"}
    card_drafts = [d for d in result.created if d.type == "card"]
    quiz_drafts = [d for d in result.created if d.type == "quiz"]
    assert len(card_drafts) == 6
    assert len(quiz_drafts) == 6


async def test_market_generation_batch_missing_entry_skips_only_that_lesson(db_session):
    """A mini-batch response missing one lesson's entry increments skipped for just
    that lesson; its batch-mates are still created."""
    gb_level, gb_lessons = await _seed_gb_level_with_n_lessons(db_session, n=3, lesson_type="quiz",
                                                               order_index=905)
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    async def fake_complete(*, system_prompt, messages, **kwargs):
        # Omit the middle lesson's entry entirely.
        keep = [gb_lessons[0], gb_lessons[2]]
        items = [
            {"source_lesson_id": str(lesson.id), "question": f"Adapted {i}",
             "choices": ["x", "y"], "answer_index": 0, "explanation": "Adapted."}
            for i, lesson in enumerate(keep)
        ]
        return json.dumps(items)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=fake_complete)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    assert mock_client.complete.await_count == 1
    assert len(result.created) == 2
    assert result.skipped == 1


async def test_market_generation_batch_llm_error_skips_only_that_batch(db_session):
    """A mini-batch whose LLM call raises skips only that mini-batch's lessons;
    other mini-batches are unaffected."""
    gb_level, gb_lessons = await _seed_gb_level_with_n_lessons(db_session, n=7, lesson_type="quiz",
                                                               order_index=906)
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    call_count = 0

    async def fake_complete(*, system_prompt, messages, **kwargs):
        nonlocal call_count
        idx = call_count
        call_count += 1
        if idx == 0:
            raise RuntimeError("LLM call failed")
        # Second batch (2 remaining lessons) succeeds.
        batch = gb_lessons[5:7]
        items = [
            {"source_lesson_id": str(lesson.id), "question": f"Adapted {i}",
             "choices": ["x", "y"], "answer_index": 0, "explanation": "Adapted."}
            for i, lesson in enumerate(batch)
        ]
        return json.dumps(items)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=fake_complete)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    assert mock_client.complete.await_count == 2
    # First batch (5 lessons) fully skipped; second batch (2 lessons) created.
    assert result.skipped == 5
    assert len(result.created) == 2


async def test_market_generation_batch_moderation_reject_flags_one_item(db_session):
    """Moderation is applied per-item in the batched path: one item flagged unsafe
    is still created (moderation_safe=False), matching single-lesson _generate_one
    behaviour, and does not affect its batch-mates."""
    gb_level, gb_lessons = await _seed_gb_level_with_n_lessons(db_session, n=2, lesson_type="quiz",
                                                               order_index=907)
    us_level = await _seed_us_level(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    async def fake_complete(*, system_prompt, messages, **kwargs):
        return _batched_quiz_response(gb_lessons)

    async def fake_moderate(text, *, surface):
        if "Adapted quiz 0" in text:
            return ModerationResult(safe=False, category="violence", text=text)
        return ModerationResult(safe=True, category=None, text=text)

    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=fake_complete)
    with patch("app.services.admin_content_generation_service.get_llm_client",
               return_value=mock_client), \
         patch("app.services.admin_content_generation_service.moderate_output",
               AsyncMock(side_effect=fake_moderate)):
        result = await generate_market_level_lessons(
            db_session, us_level, source_level=gb_level, brief=us_brief,
        )

    assert mock_client.complete.await_count == 1
    assert len(result.created) == 2
    assert result.skipped == 0
    unsafe = [d for d in result.created if not d.moderation_safe]
    safe = [d for d in result.created if d.moderation_safe]
    assert len(unsafe) == 1
    assert unsafe[0].moderation_category == "violence"
    assert len(safe) == 1


async def test_generate_market_endpoint_blocks_unverified_brief(admin_client, db_session):
    gb_level, _ = await _seed_gb_level_with_lesson(db_session)
    us_level = await _seed_us_level(db_session)
    # Draft (not verified) brief → endpoint must 409.
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="draft"))
    await db_session.flush()

    resp = await admin_client.post(
        f"/admin/levels/{us_level.id}/generate-market",
        json={"source_level_id": str(gb_level.id)},
    )
    assert resp.status_code == 409, resp.text
