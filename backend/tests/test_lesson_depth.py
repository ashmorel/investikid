from unittest.mock import patch

import pytest

from app.models.content import Level, Module
from app.models.market_brief import MarketBrief
from app.services.admin_content_generation_service import (
    generate_native_level_lessons,
    target_lessons_for_tier,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_target_per_tier():
    assert target_lessons_for_tier(1) == 10
    assert target_lessons_for_tier(2) == 15
    assert target_lessons_for_tier(3) == 20
    assert target_lessons_for_tier(None) == 15  # fallback to tier-2 count


async def _seed_level(db_session):
    mod = Module(topic="t", title="M", country_codes=[], market_code="GB",
                 is_premium=False, order_index=0, icon="📚", published=False)
    db_session.add(mod)
    await db_session.flush()
    lvl = Level(module_id=mod.id, title="L", order_index=0, is_premium=False,
                pass_threshold=0.7, learning_objectives=["o"])
    db_session.add(lvl)
    await db_session.flush()
    brief = MarketBrief(market_code="GB", brief_json={"currency": "GBP"}, status="verified")
    db_session.add(brief)
    await db_session.flush()
    return lvl, brief


def _draft_stub(concept):
    # Generator reads draft.content_json to build the sibling-avoid list.
    return type("D", (), {"content_json": {"title": f"scenario about {concept}"}})()


async def test_target_count_produces_exact_three_format_rotation(db_session):
    lvl, brief = await _seed_level(db_session)
    calls: list[tuple[str, str]] = []

    async def fake_one(session, *, level, module, concept, lesson_type, **kw):
        calls.append((concept, lesson_type))
        return _draft_stub(concept)

    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        result = await generate_native_level_lessons(
            db_session, lvl, brief=brief,
            concepts=[f"c{i}" for i in range(10)], complexity_tier=3,
            target_count=target_lessons_for_tier(3),
        )
    assert len(calls) == 20                       # tier 3 → exactly 20 lessons
    # card → quiz → scenario rotation per concept
    assert calls[0] == ("c0", "card")
    assert calls[1] == ("c0", "quiz")
    assert calls[2] == ("c0", "scenario")
    assert calls[3] == ("c1", "card")
    assert len(result.created) == 20


async def test_sibling_avoid_list_grows_across_lessons(db_session):
    lvl, brief = await _seed_level(db_session)
    avoid_sizes: list[int] = []

    async def fake_one(session, *, concept, avoid=None, **kw):
        avoid_sizes.append(len(avoid or []))
        return _draft_stub(concept)

    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        await generate_native_level_lessons(
            db_session, lvl, brief=brief,
            concepts=[f"c{i}" for i in range(5)], target_count=6,
        )
    # First lesson sees nothing to avoid; later lessons see the growing sibling set.
    assert avoid_sizes[0] == 0
    assert avoid_sizes[-1] >= 1
    assert avoid_sizes == sorted(avoid_sizes)  # monotonically non-decreasing


async def test_target_count_ten(db_session):
    lvl, brief = await _seed_level(db_session)

    async def fake_one(session, *, concept, **kw):
        return _draft_stub(concept)

    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        result = await generate_native_level_lessons(
            db_session, lvl, brief=brief,
            concepts=[f"c{i}" for i in range(5)], target_count=10,
        )
    assert len(result.created) == 10


async def test_target_count_wraps_concepts_when_too_few(db_session):
    lvl, brief = await _seed_level(db_session)
    seen: list[str] = []

    async def fake_one(session, *, concept, **kw):
        seen.append(concept)
        return _draft_stub(concept)

    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        await generate_native_level_lessons(
            db_session, lvl, brief=brief, concepts=["a", "b"], target_count=10,
        )
    # target 10, only 2 concepts → still 10 lessons, concepts reused
    assert len(seen) == 10
    assert set(seen) == {"a", "b"}


async def test_no_target_count_is_one_per_concept(db_session):
    # Ad-hoc per-level generation (e.g. create-module-from-suggestion) keeps the
    # original behaviour: exactly one lesson per concept, card/quiz alternating.
    lvl, brief = await _seed_level(db_session)
    calls: list[tuple[str, str]] = []

    async def fake_one(session, *, concept, lesson_type, **kw):
        calls.append((concept, lesson_type))
        return _draft_stub(concept)

    with patch("app.services.admin_content_generation_service._generate_one",
               side_effect=fake_one):
        result = await generate_native_level_lessons(
            db_session, lvl, brief=brief, concepts=["a", "b", "c"],
        )
    assert len(result.created) == 3
    assert calls == [("a", "card"), ("b", "quiz"), ("c", "card")]
