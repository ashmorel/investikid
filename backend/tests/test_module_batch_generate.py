import json
import re
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.services.admin_content_generation_service import (
    GenerationResult,
    generate_module_market_lessons,
)
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

US_CARD = json.dumps({"title": "Saving up", "body": "A plan for your dollars."})

US_BRIEF = {
    "currency": "USD",
    "tax_advantaged_accounts": ["Roth IRA", "529 plan"],
    "regulators": ["SEC", "FINRA"],
    "deposit_protection": "FDIC insures up to $250,000",
    "typical_products": ["savings account"],
    "local_examples": ["allowance in a piggy bank"],
    "notes": "Dollars and cents.",
}

_SOURCE_ID_RE = re.compile(r'source_lesson_id "([0-9a-fA-F-]{36})"')


async def _fake_batch_complete(*, system_prompt, messages, **kwargs):
    """Echo back one adapted card per source_lesson_id found in the batched
    prompt, so these module-batch tests (which don't care about batching
    specifics) keep working unchanged against the grouped/batched
    generate_market_level_lessons implementation."""
    ids = _SOURCE_ID_RE.findall(system_prompt)
    items = [
        {"source_lesson_id": src_id, "title": "Saving up", "body": "A plan for your dollars."}
        for src_id in ids
    ]
    return json.dumps(items)


def _llm_patches():
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(side_effect=_fake_batch_complete)
    return mock_client, patch(
        "app.services.admin_content_generation_service.get_llm_client",
        return_value=mock_client,
    ), patch(
        "app.services.admin_content_generation_service.moderate_output",
        AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x")),
    )


async def _seed_gb_module(db_session, *, topic="savings", order_index=10):
    """GB module with 2 levels (order 0, 1), each with one generatable card."""
    module = Module(
        topic=topic, title="GB Saving", country_codes=[], is_premium=False,
        order_index=order_index, icon="💷", market_code="GB", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    for order in (0, 1):
        level = Level(module_id=module.id, title=f"GB Level {order}", order_index=order,
                      is_premium=False, pass_threshold=0.7)
        db_session.add(level)
        await db_session.flush()
        db_session.add(Lesson(
            module_id=module.id, level_id=level.id, type="card", xp_reward=0,
            order_index=0,
            content_json={"title": f"ISA savings {order}",
                          "body": "Put your £ into an ISA with the FCA-regulated bank."},
        ))
    await db_session.flush()
    return module


async def _seed_us_module(db_session, *, topic="savings", order_index=10,
                          populate_first=True, levels=(0, 1)):
    """US module. By default level[0] gets a populated lesson; level[1] stays empty."""
    module = Module(
        topic=topic, title="US Saving", country_codes=[], is_premium=False,
        order_index=order_index, icon="💵", market_code="US", min_age=10, max_age=14,
    )
    db_session.add(module)
    await db_session.flush()
    made = []
    for i, order in enumerate(levels):
        level = Level(module_id=module.id, title=f"US Level {order}", order_index=order,
                      is_premium=False, pass_threshold=0.7)
        db_session.add(level)
        await db_session.flush()
        made.append(level)
        if i == 0 and populate_first:
            db_session.add(Lesson(
                module_id=module.id, level_id=level.id, type="card", xp_reward=0,
                order_index=0,
                content_json={"title": "Existing", "body": "Already has dollars."},
            ))
    await db_session.flush()
    return module, made


async def _draft_count(db_session, level_id):
    rows = (await db_session.scalars(
        select(LessonDraft).where(LessonDraft.level_id == level_id)
    )).all()
    return len(rows)


async def test_skip_populated_generates_only_empty_levels(db_session):
    await _seed_gb_module(db_session)
    us_module, us_levels = await _seed_us_module(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client, p_client, p_mod = _llm_patches()
    with p_client, p_mod:
        summary = await generate_module_market_lessons(
            db_session, us_module, brief=us_brief, include_populated=False,
        )

    assert summary["generated"] == 1
    assert summary["skipped_populated"] == 1
    assert summary["skipped_no_source"] == 0
    # level[1] (empty) generated; level[0] (populated) skipped — no drafts.
    assert await _draft_count(db_session, us_levels[1].id) >= 1
    assert await _draft_count(db_session, us_levels[0].id) == 0


async def test_include_populated_generates_all(db_session):
    await _seed_gb_module(db_session)
    us_module, us_levels = await _seed_us_module(db_session)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client, p_client, p_mod = _llm_patches()
    with p_client, p_mod:
        summary = await generate_module_market_lessons(
            db_session, us_module, brief=us_brief, include_populated=True,
        )

    assert summary["generated"] == 2
    assert summary["skipped_populated"] == 0
    assert await _draft_count(db_session, us_levels[0].id) >= 1
    assert await _draft_count(db_session, us_levels[1].id) >= 1


async def test_skip_levels_with_pending_drafts(db_session):
    """Re-running a batch must NOT stack duplicate drafts: a level that already
    has pending drafts (but no published lessons) is skipped."""
    await _seed_gb_module(db_session)
    us_module, us_levels = await _seed_us_module(db_session, populate_first=False)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    # level[0] already has a pending draft from an earlier run; level[1] is empty.
    db_session.add(LessonDraft(
        level_id=us_levels[0].id, type="card",
        content_json={"title": "old", "body": "from a prior run"}, concept="c",
        model_used="t", moderation_safe=True, moderation_category=None,
    ))
    await db_session.flush()

    mock_client, p_client, p_mod = _llm_patches()
    with p_client, p_mod:
        summary = await generate_module_market_lessons(
            db_session, us_module, brief=us_brief, include_populated=False,
        )

    assert summary["generated"] == 1
    assert summary["skipped_has_drafts"] == 1
    assert summary["skipped_populated"] == 0
    # level[0] keeps its single existing draft (not stacked); level[1] generated.
    assert await _draft_count(db_session, us_levels[0].id) == 1
    assert await _draft_count(db_session, us_levels[1].id) >= 1


async def test_no_gb_source_skips_all(db_session):
    # US module with no GB match (topic/order_index that doesn't exist in GB).
    us_module, us_levels = await _seed_us_module(
        db_session, topic="zzz", order_index=99, populate_first=False, levels=(0,),
    )
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    await db_session.flush()

    mock_client, p_client, p_mod = _llm_patches()
    with p_client, p_mod:
        summary = await generate_module_market_lessons(
            db_session, us_module, brief=us_brief, include_populated=False,
        )

    assert summary["generated"] == 0
    assert summary["skipped_no_source"] == 1
    assert mock_client.complete.await_count == 0


async def test_endpoint_returns_summary(admin_client, db_session):
    await _seed_gb_module(db_session)
    us_module, _ = await _seed_us_module(db_session)
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified"))
    await db_session.flush()

    mock_client, p_client, p_mod = _llm_patches()
    with p_client, p_mod:
        resp = await admin_client.post(
            f"/admin/modules/{us_module.id}/generate-market",
            json={"include_populated": False},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("generated", "skipped_populated", "skipped_has_drafts",
                "skipped_no_source", "errored", "levels"):
        assert key in body
    assert body["generated"] == 1
    assert body["skipped_populated"] == 1


async def test_endpoint_blocks_unverified_brief(admin_client, db_session):
    await _seed_gb_module(db_session)
    us_module, _ = await _seed_us_module(db_session)
    db_session.add(MarketBrief(market_code="US", brief_json=US_BRIEF, status="draft"))
    await db_session.flush()

    resp = await admin_client.post(
        f"/admin/modules/{us_module.id}/generate-market",
        json={"include_populated": False},
    )
    assert resp.status_code == 409, resp.text


async def test_endpoint_unknown_module_404(admin_client):
    import uuid

    resp = await admin_client.post(
        f"/admin/modules/{uuid.uuid4()}/generate-market",
        json={"include_populated": False},
    )
    assert resp.status_code == 404, resp.text


async def test_failed_level_rolls_back_and_does_not_leak_drafts(db_session):
    """A level that fails mid-generation (after a flush) must NOT leak its
    partial drafts into the next level's commit — the except handler rolls back."""
    await _seed_gb_module(db_session, topic="leak", order_index=20)
    us_module, us_levels = await _seed_us_module(
        db_session, topic="leak", order_index=20, populate_first=False,
    )
    # Capture ids while the objects are live (the seed commit below expires them).
    level0_id = next(lv.id for lv in us_levels if lv.order_index == 0)
    level1_id = next(lv.id for lv in us_levels if lv.order_index == 1)
    us_brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(us_brief)
    # Commit the seed: in prod the modules/levels already exist, so a failed
    # level's rollback only discards that level's in-flight drafts, not the seed.
    await db_session.commit()

    async def fake_generate(session, target_level, *, source_level, brief):
        # Simulate partial work then a mid-level failure on the order-0 level;
        # the order-1 level succeeds and commits (which, without a rollback,
        # would also persist the failed level's leaked draft).
        session.add(LessonDraft(
            level_id=target_level.id, type="card",
            content_json={"title": "x", "body": "y"}, concept="c",
            model_used="t", moderation_safe=True, moderation_category=None,
        ))
        await session.flush()
        if target_level.order_index == 0:
            raise RuntimeError("boom")
        await session.commit()
        return GenerationResult(created=[], skipped=0)

    with patch(
        "app.services.admin_content_generation_service.generate_market_level_lessons",
        side_effect=fake_generate,
    ):
        summary = await generate_module_market_lessons(
            db_session, us_module, brief=us_brief, include_populated=False,
        )

    assert summary["errored"] == 1
    assert summary["generated"] == 1
    failed_drafts = await db_session.scalar(
        select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level0_id)
    )
    ok_drafts = await db_session.scalar(
        select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level1_id)
    )
    assert failed_drafts == 0  # rolled back, not leaked
    assert ok_drafts == 1
