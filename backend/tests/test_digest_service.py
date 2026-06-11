"""Tests for the weekly parent digest builder + runner (W4 Task 2)."""
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.content import Lesson, LessonCompletion, Level, LevelMastery, Module
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User
from app.services import digest_service

pytestmark = pytest.mark.asyncio(loop_scope="session")

NOW = datetime(2026, 6, 11, 9, 0, tzinfo=UTC)


class FakeSender:
    def __init__(self):
        self.calls = []

    async def send(self, session, to, template, context, subject_id=None):
        self.calls.append({"to": to, "template": template, "context": context})


@pytest.fixture
def fake_sender(monkeypatch):
    sender = FakeSender()
    monkeypatch.setattr(digest_service, "get_email_sender", lambda: sender)
    return sender


def _child(parent_email, username=None):
    return User(
        username=username or f"kid_{uuid.uuid4().hex[:8]}",
        password_hash="x",
        dob=date(2014, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent_email,
    )


def _module(*, title="Saving Basics", prompt=None, order_index=0):
    return Module(
        topic="saving",
        title=title,
        country_codes=["GB"],
        order_index=order_index,
        conversation_prompt=prompt,
    )


def _level(module, *, title="Level 1", objectives=None):
    return Level(
        module_id=module.id,
        title=title,
        order_index=0,
        learning_objectives=objectives,
    )


def _mastery(user, level, *, when):
    return LevelMastery(user_id=user.id, level_id=level.id, mastered_at=when, score=0.9)


async def _add_completion(db_session, user, module, *, when):
    lesson = Lesson(
        module_id=module.id, type="quiz", content_json={}, order_index=0,
    )
    db_session.add(lesson)
    await db_session.flush()
    db_session.add(LessonCompletion(user_id=user.id, lesson_id=lesson.id, completed_at=when))
    await db_session.flush()
    return lesson


async def _setup_active_child(db_session, parent_email, *, objectives=None, prompt="Talk about saving!"):
    """Child with a level mastery inside the 7-day window."""
    child = _child(parent_email)
    module = _module(prompt=prompt)
    db_session.add_all([child, module])
    await db_session.flush()
    level = _level(module, objectives=objectives)
    db_session.add(level)
    await db_session.flush()
    db_session.add(_mastery(child, level, when=NOW - timedelta(days=2)))
    await db_session.flush()
    return child, module, level


# --- build_weekly_digest -----------------------------------------------------

async def test_build_returns_none_for_quiet_week(db_session):
    db_session.add(_child("quiet@example.com"))
    await db_session.flush()

    digest = await digest_service.build_weekly_digest(
        db_session, "quiet@example.com", now=NOW
    )

    assert digest is None


async def test_build_includes_mastery_objectives_and_prompt(db_session):
    child, module, level = await _setup_active_child(
        db_session, "obj@example.com",
        objectives=["Know what saving means", "Spot needs vs wants"],
    )

    digest = await digest_service.build_weekly_digest(db_session, "obj@example.com", now=NOW)

    assert digest is not None
    assert len(digest["children"]) == 1
    entry = digest["children"][0]
    assert entry["name"] == child.username
    assert entry["masteries"] == [{
        "module_title": module.title,
        "level_title": level.title,
        "objectives": ["Know what saving means", "Spot needs vs wants"],
    }]
    assert entry["streak"] == 0
    assert entry["conversation_prompt"] == "Talk about saving!"
    assert digest["parent_subscribed"] is False


async def test_build_multi_child_aggregation(db_session):
    parent = "multi@example.com"
    child_a, _, _ = await _setup_active_child(db_session, parent)
    child_b = _child(parent)
    module_b = _module(title="Money Jobs", order_index=1)
    db_session.add_all([child_b, module_b])
    await db_session.flush()
    await _add_completion(db_session, child_b, module_b, when=NOW - timedelta(days=1))

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    assert digest is not None
    names = {c["name"] for c in digest["children"]}
    assert names == {child_a.username, child_b.username}
    by_name = {c["name"]: c for c in digest["children"]}
    assert by_name[child_b.username]["lessons_completed"] == 1


async def test_build_window_excludes_old_activity(db_session):
    parent = "old@example.com"
    child = _child(parent)
    module = _module()
    db_session.add_all([child, module])
    await db_session.flush()
    level = _level(module)
    db_session.add(level)
    await db_session.flush()
    # Mastery 10 days ago — outside the 7-day first-send window.
    db_session.add(_mastery(child, level, when=NOW - timedelta(days=10)))
    await db_session.flush()

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    assert digest is None


async def test_build_window_starts_at_last_digest_sent(db_session):
    parent = "window@example.com"
    child = _child(parent)
    module = _module()
    db_session.add_all([child, module])
    db_session.add(ParentPreferences(
        parent_email=parent, last_digest_sent_at=NOW - timedelta(days=3),
    ))
    await db_session.flush()
    level = _level(module)
    db_session.add(level)
    await db_session.flush()
    # Mastery 5 days ago — inside 7d but BEFORE the last digest → excluded.
    db_session.add(_mastery(child, level, when=NOW - timedelta(days=5)))
    await db_session.flush()

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    assert digest is None


async def test_build_prompt_falls_back_to_recommended_module(db_session, monkeypatch):
    parent = "fallback@example.com"
    child = _child(parent)
    # Mastered module has NO prompt; the recommended module has one.
    mastered_module = _module(title="No Prompt Module", prompt=None)
    rec_module = _module(title="Shares 101", prompt="Ask about shares!", order_index=1)
    db_session.add_all([child, mastered_module, rec_module])
    await db_session.flush()
    level = _level(mastered_module)
    db_session.add(level)
    await db_session.flush()
    db_session.add(_mastery(child, level, when=NOW - timedelta(days=1)))
    await db_session.flush()

    async def fake_recs(session, user):
        return {
            "continue_learning": [],
            "practise_again": [],
            "something_new": [{
                "module_id": rec_module.id,
                "lesson_id": None,
                "level_id": None,
                "level_title": None,
                "score": 1.0,
                "reason": "New topic",
                "review_prompt": None,
                "weak_concepts": [],
            }],
            "review_summary": {"due_count": 0, "next_due_at": None},
        }

    monkeypatch.setattr(digest_service, "get_recommendations", fake_recs)

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    entry = digest["children"][0]
    assert entry["conversation_prompt"] == "Ask about shares!"
    assert entry["next_recommendation"]["module_title"] == "Shares 101"


async def test_build_subscribed_parent_flag(db_session):
    parent = "subbed@example.com"
    await _setup_active_child(db_session, parent)
    db_session.add(Subscription(
        parent_email=parent,
        provider="stripe",
        external_id=f"ext-{uuid.uuid4()}",
        status="active",
        current_period_end=NOW + timedelta(days=30),
    ))
    await db_session.flush()

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    assert digest["parent_subscribed"] is True


async def test_build_survives_enrichment_failure(db_session, monkeypatch):
    parent = "enrich@example.com"
    await _setup_active_child(db_session, parent)

    async def boom(session, user_id):
        raise RuntimeError("enrichment down")

    monkeypatch.setattr(digest_service, "get_strengths_and_gaps", boom)

    digest = await digest_service.build_weekly_digest(db_session, parent, now=NOW)

    assert digest is not None
    assert digest["children"][0].get("weak_topic") is None


# --- run_weekly_digests ------------------------------------------------------

async def test_run_first_send_with_activity(db_session, fake_sender):
    parent = "run1@example.com"
    await _setup_active_child(db_session, parent)

    result = await digest_service.run_weekly_digests(db_session, now=NOW)

    assert result["sent"] == 1
    assert len(fake_sender.calls) == 1
    call = fake_sender.calls[0]
    assert call["to"] == parent
    assert call["template"] == "weekly_digest"
    assert call["context"]["children"]
    pref = await db_session.get(ParentPreferences, parent)
    assert pref is not None
    assert pref.last_digest_sent_at == NOW


async def test_run_quiet_week_not_sent_last_sent_untouched(db_session, fake_sender):
    parent = "run2@example.com"
    db_session.add(_child(parent))
    old_sent = NOW - timedelta(days=10)
    db_session.add(ParentPreferences(parent_email=parent, last_digest_sent_at=old_sent))
    await db_session.flush()

    result = await digest_service.run_weekly_digests(db_session, now=NOW)

    assert result["sent"] == 0
    assert result["skipped_quiet"] == 1
    assert fake_sender.calls == []
    pref = await db_session.get(ParentPreferences, parent)
    assert pref.last_digest_sent_at == old_sent


async def test_run_skips_opted_out(db_session, fake_sender):
    parent = "run3@example.com"
    await _setup_active_child(db_session, parent)
    db_session.add(ParentPreferences(parent_email=parent, weekly_digest_opt_out=True))
    await db_session.flush()

    result = await digest_service.run_weekly_digests(db_session, now=NOW)

    assert result["sent"] == 0
    assert result["skipped_opt_out"] == 1
    assert fake_sender.calls == []


async def test_run_skips_recently_sent(db_session, fake_sender):
    parent = "run4@example.com"
    await _setup_active_child(db_session, parent)
    recent = NOW - timedelta(days=3)
    db_session.add(ParentPreferences(parent_email=parent, last_digest_sent_at=recent))
    await db_session.flush()

    result = await digest_service.run_weekly_digests(db_session, now=NOW)

    assert result["sent"] == 0
    assert result["skipped_recent"] == 1
    assert fake_sender.calls == []
    pref = await db_session.get(ParentPreferences, parent)
    assert pref.last_digest_sent_at == recent


async def test_run_multi_child_one_email(db_session, fake_sender):
    parent = "run5@example.com"
    child_a, _, _ = await _setup_active_child(db_session, parent)
    child_b = _child(parent)
    module_b = _module(title="Budgeting", order_index=1)
    db_session.add_all([child_b, module_b])
    await db_session.flush()
    await _add_completion(db_session, child_b, module_b, when=NOW - timedelta(days=1))

    result = await digest_service.run_weekly_digests(db_session, now=NOW)

    assert result["sent"] == 1
    assert len(fake_sender.calls) == 1
    names = {c["name"] for c in fake_sender.calls[0]["context"]["children"]}
    assert names == {child_a.username, child_b.username}
