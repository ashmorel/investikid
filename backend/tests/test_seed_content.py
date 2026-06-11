import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.seed.content import (
    _MODULES,
    _insert_position,
    _lesson_identity,
    seed_modules_and_lessons,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_every_module_has_at_least_five_questions_or_scenarios():
    """Each module's level must offer >= 5 quiz/scenario lessons."""
    for spec in _MODULES:
        qs = [le for le in spec["lessons"] if le["type"] in ("quiz", "scenario")]
        assert len(qs) >= 5, (
            f"module {spec['title']!r} has only {len(qs)} quiz/scenario lessons (need >=5)"
        )


def test_quiz_and_scenario_specs_are_well_formed():
    for spec in _MODULES:
        for le in spec["lessons"]:
            cj = le["content_json"]
            if le["type"] == "quiz":
                assert cj.get("question"), f"empty quiz question in {spec['title']!r}"
                assert cj.get("explanation"), f"empty explanation in {spec['title']!r}"
                choices = cj.get("choices") or []
                assert len(choices) >= 2
                assert isinstance(cj.get("answer_index"), int)
                assert 0 <= cj["answer_index"] < len(choices), (
                    f"answer_index out of range in {spec['title']!r}"
                )
            elif le["type"] == "scenario":
                assert cj.get("prompt"), f"empty scenario prompt in {spec['title']!r}"
                choices = cj.get("choices") or []
                assert len(choices) >= 2
                assert isinstance(cj.get("correct_index"), int)
                assert 0 <= cj["correct_index"] < len(choices)
                for ch in choices:
                    assert ch.get("label") and ch.get("outcome"), (
                        f"scenario choice missing label/outcome in {spec['title']!r}"
                    )


def test_every_module_first_lesson_is_card():
    """Every module must open with a card (foundational intro)."""
    for spec in _MODULES:
        first = spec["lessons"][0]
        assert first["type"] == "card", (
            f"module {spec['title']!r}: first lesson is {first['type']!r}, expected 'card'"
        )


def test_scenarios_not_before_first_quiz():
    """Within each module, scenarios must not appear before the first quiz or card.

    Concretely: the index of the first scenario must be greater than the index of
    the first quiz (a light pedagogical-order guard).  Modules with no scenario or
    no quiz are skipped.
    """
    for spec in _MODULES:
        lessons = spec["lessons"]
        scenario_indices = [i for i, le in enumerate(lessons) if le["type"] == "scenario"]
        quiz_indices = [i for i, le in enumerate(lessons) if le["type"] == "quiz"]
        if not scenario_indices or not quiz_indices:
            continue
        first_scenario = scenario_indices[0]
        first_quiz = quiz_indices[0]
        assert first_scenario > first_quiz, (
            f"module {spec['title']!r}: first scenario (index {first_scenario}) "
            f"appears before first quiz (index {first_quiz})"
        )


def test_insert_position_slots_into_type_band():
    """A newly-appended lesson lands at the END of its difficulty band:
    cards -> video -> quizzes -> scenarios, without reordering existing lessons."""
    seq = ["card", "card", "video", "quiz", "scenario"]
    # A new card goes after the existing cards (index 2), before the video.
    assert _insert_position(seq, "card") == 2
    # A new video goes after the existing video (index 3).
    assert _insert_position(seq, "video") == 3
    # A new quiz goes after the existing quiz (index 4), before the scenario.
    assert _insert_position(seq, "quiz") == 4
    # A new scenario goes at the very end (index 5).
    assert _insert_position(seq, "scenario") == 5
    # Empty level -> position 0.
    assert _insert_position([], "quiz") == 0
    # All scenarios -> a new quiz slots in front of them.
    assert _insert_position(["scenario", "scenario"], "quiz") == 0


async def _count_lessons_for(session, topic, title) -> int:
    module = await session.scalar(
        select(Module).where(Module.topic == topic, Module.title == title)
    )
    assert module is not None
    return await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.module_id == module.id)
    )


async def test_seed_is_idempotent_and_meets_criterion(db_session):
    # First seed creates everything.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    spec = _MODULES[0]
    count_after_first = await _count_lessons_for(db_session, spec["topic"], spec["title"])
    # _count_lessons_for counts ALL lessons in the module (across every level),
    # so include any extra_levels (e.g. the "What is a Stock?" Level 2/3 pilot).
    expected_lessons = len(spec["lessons"]) + sum(
        len(lv["lessons"]) for lv in spec.get("extra_levels", [])
    )
    assert count_after_first == expected_lessons

    # A level should expose >= 5 quiz/scenario lessons.
    module = await db_session.scalar(
        select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
    )
    level = await db_session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 0)
    )
    lessons = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).all()
    qs = [le for le in lessons if le.type in ("quiz", "scenario")]
    assert len(qs) >= 5

    # Second seed must add nothing (idempotent).
    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    count_after_second = await _count_lessons_for(db_session, spec["topic"], spec["title"])
    assert count_after_second == count_after_first

    # On a fresh DB the seeded order matches the curriculum spec exactly.
    lessons_after = (await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id)
    )).all()
    by_ident = {_lesson_identity(le.type, le.content_json): le for le in lessons_after}
    for i, lesson_spec in enumerate(spec["lessons"]):
        ident = _lesson_identity(lesson_spec["type"], lesson_spec["content_json"])
        le = by_ident.get(ident)
        assert le is not None, f"lesson not found in DB: {ident!r}"
        assert le.order_index == i, (
            f"lesson {ident!r}: expected order_index={i}, got {le.order_index}"
        )


async def test_reseed_preserves_manual_reorder(db_session):
    """A manual admin reorder must survive re-seeding: the seeder only places
    new lessons, it never re-sorts lessons already positioned."""
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    spec = _MODULES[0]
    module = await db_session.scalar(
        select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
    )
    level = await db_session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 0)
    )
    lessons = list((await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())

    # Simulate an admin manually reversing the lesson order (via OrderArrows).
    reversed_lessons = list(reversed(lessons))
    for i, le in enumerate(reversed_lessons):
        le.order_index = i
    await db_session.flush()
    expected_order = [le.id for le in reversed_lessons]

    # Re-seed: must NOT reset to the curriculum order.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    after = list((await db_session.scalars(
        select(Lesson).where(Lesson.level_id == level.id).order_by(Lesson.order_index)
    )).all())
    assert [le.id for le in after] == expected_order


def _fake_spec(**overrides):
    """Minimal module spec for exercising the seeder in isolation."""
    spec = {
        "topic": "w3a_fake",
        "title": "W3a Fake Module",
        "country_codes": [],
        "is_premium": False,
        "order_index": 99,
        "icon": "🧪",
        "lessons": [
            {"type": "card", "xp_reward": 10, "content_json": {
                "title": "Fake card", "body": "Fake body",
            }},
        ],
        "extra_levels": [
            {"title": "Level 2", "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Fake L2 card", "body": "Fake L2 body",
                }},
            ]},
        ],
    }
    spec.update(overrides)
    return spec


async def _fetch_module_and_levels(session, spec):
    module = await session.scalar(
        select(Module).where(Module.topic == spec["topic"], Module.title == spec["title"])
    )
    assert module is not None
    level1 = await session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 0)
    )
    level2 = await session.scalar(
        select(Level).where(Level.module_id == module.id, Level.order_index == 1)
    )
    return module, level1, level2


async def test_seed_applies_standards_sources_objectives(db_session, monkeypatch):
    """On create, the seeder applies standards_alignment/sources to the module
    and learning_objectives to Level 1 and extra levels; re-seeding is idempotent."""
    spec = _fake_spec(
        standards_alignment=[{"framework": "FCA", "code": "F1"}],
        sources=[{"title": "Source A", "url": "https://example.com/a"}],
        learning_objectives=["Understand fake things"],
        extra_levels=[{
            "title": "Level 2",
            "learning_objectives": ["Apply fake things"],
            "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Fake L2 card", "body": "Fake L2 body",
                }},
            ],
        }],
    )
    monkeypatch.setattr("app.seed.content._MODULES", [spec])

    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, level1, level2 = await _fetch_module_and_levels(db_session, spec)
    assert module.standards_alignment == [{"framework": "FCA", "code": "F1"}]
    assert module.sources == [{"title": "Source A", "url": "https://example.com/a"}]
    assert level1.learning_objectives == ["Understand fake things"]
    assert level2 is not None
    assert level2.learning_objectives == ["Apply fake things"]

    # Re-seed: values unchanged, no duplicate levels.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    module, level1, level2 = await _fetch_module_and_levels(db_session, spec)
    assert module.standards_alignment == [{"framework": "FCA", "code": "F1"}]
    assert module.sources == [{"title": "Source A", "url": "https://example.com/a"}]
    assert level1.learning_objectives == ["Understand fake things"]
    assert level2.learning_objectives == ["Apply fake things"]
    level_count = await db_session.scalar(
        select(func.count()).select_from(Level).where(Level.module_id == module.id)
    )
    assert level_count == 2


async def test_seed_applies_metadata_on_update_path(db_session, monkeypatch):
    """When a module already exists, a spec that gains the keys updates the rows."""
    bare = _fake_spec()
    monkeypatch.setattr("app.seed.content._MODULES", [bare])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, level1, level2 = await _fetch_module_and_levels(db_session, bare)
    assert module.standards_alignment is None
    assert level1.learning_objectives is None

    enriched = _fake_spec(
        standards_alignment=[{"framework": "FCA", "code": "F2"}],
        sources=[{"title": "Source B", "url": "https://example.com/b"}],
        learning_objectives=["Updated objective"],
        extra_levels=[{
            "title": "Level 2",
            "learning_objectives": ["Updated L2 objective"],
            "lessons": [
                {"type": "card", "xp_reward": 10, "content_json": {
                    "title": "Fake L2 card", "body": "Fake L2 body",
                }},
            ],
        }],
    )
    monkeypatch.setattr("app.seed.content._MODULES", [enriched])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, level1, level2 = await _fetch_module_and_levels(db_session, enriched)
    assert module.standards_alignment == [{"framework": "FCA", "code": "F2"}]
    assert module.sources == [{"title": "Source B", "url": "https://example.com/b"}]
    assert level1.learning_objectives == ["Updated objective"]
    assert level2.learning_objectives == ["Updated L2 objective"]


def test_every_module_has_conversation_prompt():
    """All 12 authored modules carry a non-empty conversation_prompt <= 300 chars."""
    assert len(_MODULES) == 12
    for spec in _MODULES:
        prompt = spec.get("conversation_prompt")
        assert isinstance(prompt, str) and prompt.strip(), (
            f"module {spec['title']!r} missing conversation_prompt"
        )
        assert len(prompt) <= 300, (
            f"module {spec['title']!r}: conversation_prompt is {len(prompt)} chars (max 300)"
        )


async def test_seed_applies_conversation_prompt_on_create_and_update(db_session, monkeypatch):
    """The seeder upserts conversation_prompt on both create and update paths."""
    spec = _fake_spec(conversation_prompt="Ask them about fake things.")
    monkeypatch.setattr("app.seed.content._MODULES", [spec])

    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, spec)
    assert module.conversation_prompt == "Ask them about fake things."

    # Update path: existing module, spec carries a new prompt.
    updated = _fake_spec(conversation_prompt="Ask them about updated fake things.")
    monkeypatch.setattr("app.seed.content._MODULES", [updated])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, updated)
    assert module.conversation_prompt == "Ask them about updated fake things."

    # Idempotent re-seed: value unchanged.
    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    module, _, _ = await _fetch_module_and_levels(db_session, updated)
    assert module.conversation_prompt == "Ask them about updated fake things."


async def test_seed_without_prompt_key_leaves_manual_value_untouched(db_session, monkeypatch):
    """A spec lacking conversation_prompt must not null out a manually-set value."""
    bare = _fake_spec()
    monkeypatch.setattr("app.seed.content._MODULES", [bare])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, bare)
    assert module.conversation_prompt is None
    module.conversation_prompt = "Manual prompt"
    await db_session.flush()

    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    module, _, _ = await _fetch_module_and_levels(db_session, bare)
    assert module.conversation_prompt == "Manual prompt"


async def test_seed_without_keys_leaves_manual_values_untouched(db_session, monkeypatch):
    """A spec lacking the keys must not null out values set manually on rows."""
    bare = _fake_spec()
    monkeypatch.setattr("app.seed.content._MODULES", [bare])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, level1, level2 = await _fetch_module_and_levels(db_session, bare)
    module.standards_alignment = [{"framework": "Manual", "code": "M1"}]
    module.sources = [{"title": "Manual source", "url": "https://example.com/m"}]
    level1.learning_objectives = ["Manual objective"]
    level2.learning_objectives = ["Manual L2 objective"]
    await db_session.flush()

    # Re-seed with the same bare spec (no metadata keys).
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, level1, level2 = await _fetch_module_and_levels(db_session, bare)
    assert module.standards_alignment == [{"framework": "Manual", "code": "M1"}]
    assert module.sources == [{"title": "Manual source", "url": "https://example.com/m"}]
    assert level1.learning_objectives == ["Manual objective"]
    assert level2.learning_objectives == ["Manual L2 objective"]


async def test_seed_applies_age_bounds_on_create(db_session, monkeypatch):
    """On create, min_age/max_age from the spec land on the module."""
    spec = _fake_spec(min_age=14, max_age=18)
    monkeypatch.setattr("app.seed.content._MODULES", [spec])

    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, spec)
    assert module.min_age == 14
    assert module.max_age == 18


async def test_seed_applies_age_bounds_on_update(db_session, monkeypatch):
    """An existing module gains age bounds when the spec adds the keys."""
    bare = _fake_spec()
    monkeypatch.setattr("app.seed.content._MODULES", [bare])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, bare)
    assert module.min_age is None
    assert module.max_age is None

    enriched = _fake_spec(min_age=14)
    monkeypatch.setattr("app.seed.content._MODULES", [enriched])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, enriched)
    assert module.min_age == 14


async def test_seed_without_age_keys_leaves_manual_values(db_session, monkeypatch):
    """A spec with no min_age/max_age keys never clobbers manually-set bounds."""
    bare = _fake_spec()
    monkeypatch.setattr("app.seed.content._MODULES", [bare])
    await seed_modules_and_lessons(db_session)
    await db_session.flush()

    module, _, _ = await _fetch_module_and_levels(db_session, bare)
    module.min_age = 16  # manual admin edit
    await db_session.flush()

    await seed_modules_and_lessons(db_session)
    await db_session.flush()
    module, _, _ = await _fetch_module_and_levels(db_session, bare)
    assert module.min_age == 16
