"""Tests for POST /diagnostic/submit (Task 3 — server-side scoring).

TDD: tests written first, run → fail, then implementation lands.

Coverage:
- fully-correct submit → overall_score==1.0 + per-topic rows match
- mixed submit scores correctly (1 of 2 per topic)
- empty session → kind="skipped", overall_score None, no topic rows
- times_correct bumped ONLY on correctly-answered items
- TopicMastery rows warm-started for answered topics
- another user's session → 403/404
- already-completed session → 409
- NO XP/streak/coins side-effect (progress unchanged after submit)
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.diagnostic import DiagnosticItem
from app.models.mastery import DiagnosticSession, MasteryCheckpoint, MasteryCheckpointTopic
from app.models.skill_profile import TopicMastery
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_MARKET = "GB"


def _make_item(
    db_session,
    *,
    topic: str = "budgeting",
    difficulty_tier: int = 1,
    market_code: str = _DEFAULT_MARKET,
    status: str = "approved",
    answer_index: int = 0,
) -> DiagnosticItem:
    item = DiagnosticItem(
        market_code=market_code,
        topic=topic,
        difficulty_tier=difficulty_tier,
        question=f"What is {topic}? (tier {difficulty_tier})",
        choices=["A", "B", "C", "D"],
        answer_index=answer_index,
        explanation="Because reasons.",
        status=status,
        source="authored",
    )
    db_session.add(item)
    return item


async def _seed_item(db_session, **kwargs) -> DiagnosticItem:
    item = _make_item(db_session, **kwargs)
    await db_session.flush()
    return item


async def _login(client, email: str, password: str) -> None:
    await client.post("/auth/login", json={"email": email, "password": password})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _register_and_login(client, db_session, *, suffix: str = "") -> User:
    """Register a new user, log them in, return the ORM User row."""
    email = f"subm{suffix}@example.com"
    username = f"submkid{suffix}"
    payload = {
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"subm_parent{suffix}@example.com",
    }
    await client.post("/auth/register", json=payload)
    await _login(client, email, "SecurePass123!")
    return await db_session.scalar(select(User).where(User.username == username))


async def _create_session(db_session, user: User, items: list[DiagnosticItem], *, kind: str = "baseline") -> DiagnosticSession:
    """Create an open DiagnosticSession with the given items."""
    diag = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind=kind,
        item_ids=[str(i.id) for i in items],
    )
    db_session.add(diag)
    await db_session.flush()
    return diag


async def _get_progress(client) -> dict:
    resp = await client.get("/users/me/progress")
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Fully-correct submit → overall_score==1.0, per-topic rows, calibration
# ---------------------------------------------------------------------------


async def test_fully_correct_submit(client, db_session):
    """All answers correct → overall_score==1.0, per-topic rows have correct==attempted."""
    user = await _register_and_login(client, db_session, suffix="_fc")

    item_bud = await _seed_item(db_session, topic="budgeting", answer_index=1)
    item_sav = await _seed_item(db_session, topic="savings", answer_index=2)
    diag = await _create_session(db_session, user, [item_bud, item_sav])

    answers = {str(item_bud.id): 1, str(item_sav.id): 2}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["overall_score"] == pytest.approx(1.0)
    assert data["kind"] == "baseline"
    assert data["session_count"] == 0

    topics = {t["topic"]: t for t in data["topics"]}
    assert topics["budgeting"]["correct"] == 1
    assert topics["budgeting"]["attempted"] == 1
    assert topics["savings"]["correct"] == 1
    assert topics["savings"]["attempted"] == 1

    # Verify MasteryCheckpoint row written
    checkpoint = await db_session.scalar(
        select(MasteryCheckpoint).where(MasteryCheckpoint.user_id == user.id)
    )
    assert checkpoint is not None
    assert checkpoint.overall_score == pytest.approx(1.0)

    # Verify topic rows in DB
    topic_rows = (await db_session.scalars(
        select(MasteryCheckpointTopic).where(MasteryCheckpointTopic.checkpoint_id == checkpoint.id)
    )).all()
    assert len(topic_rows) == 2
    for row in topic_rows:
        assert row.correct == row.attempted == 1


# ---------------------------------------------------------------------------
# Mixed submit scores correctly (1 correct out of 2 per topic)
# ---------------------------------------------------------------------------


async def test_mixed_submit_scores_correctly(client, db_session):
    """Mixed answers: 1 correct, 1 wrong per topic → overall_score==0.5."""
    user = await _register_and_login(client, db_session, suffix="_mx")

    # 2 budgeting items: answer_index 0 and 1
    item1 = await _seed_item(db_session, topic="budgeting", answer_index=0)
    item2 = await _seed_item(db_session, topic="budgeting", answer_index=1)
    diag = await _create_session(db_session, user, [item1, item2])

    # answer item1 correctly (0), item2 wrongly (0 instead of 1)
    answers = {str(item1.id): 0, str(item2.id): 0}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["overall_score"] == pytest.approx(0.5)

    topics = {t["topic"]: t for t in data["topics"]}
    assert topics["budgeting"]["correct"] == 1
    assert topics["budgeting"]["attempted"] == 2


# ---------------------------------------------------------------------------
# Empty session → kind="skipped", overall_score None, no topic rows
# ---------------------------------------------------------------------------


async def test_empty_session_skipped(client, db_session):
    """A session with item_ids=[] → kind='skipped', overall_score None, no topics."""
    user = await _register_and_login(client, db_session, suffix="_emp")

    diag = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[],
    )
    db_session.add(diag)
    await db_session.flush()

    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": {}})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["kind"] == "skipped"
    assert data["overall_score"] is None
    assert data["topics"] == []

    # Verify DB row
    checkpoint = await db_session.scalar(
        select(MasteryCheckpoint).where(MasteryCheckpoint.user_id == user.id)
    )
    assert checkpoint is not None
    assert checkpoint.kind == "skipped"
    assert checkpoint.overall_score is None

    topic_rows = (await db_session.scalars(
        select(MasteryCheckpointTopic).where(MasteryCheckpointTopic.checkpoint_id == checkpoint.id)
    )).all()
    assert len(topic_rows) == 0


# ---------------------------------------------------------------------------
# times_correct bumped ONLY on correctly-answered items
# ---------------------------------------------------------------------------


async def test_times_correct_calibration(client, db_session):
    """times_correct incremented only for correct answers."""
    user = await _register_and_login(client, db_session, suffix="_cal")

    item_right = await _seed_item(db_session, topic="budgeting", answer_index=0)
    item_wrong = await _seed_item(db_session, topic="savings", answer_index=1)
    before_right = item_right.times_correct
    before_wrong = item_wrong.times_correct

    diag = await _create_session(db_session, user, [item_right, item_wrong])

    # Answer item_right correctly, item_wrong incorrectly (give answer_index 0 when correct is 1)
    answers = {str(item_right.id): 0, str(item_wrong.id): 0}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    await db_session.refresh(item_right)
    await db_session.refresh(item_wrong)

    assert item_right.times_correct == before_right + 1
    assert item_wrong.times_correct == before_wrong  # unchanged


# ---------------------------------------------------------------------------
# TopicMastery warm-start
# ---------------------------------------------------------------------------


async def test_topic_mastery_warm_started(client, db_session):
    """TopicMastery rows created for answered topics."""
    user = await _register_and_login(client, db_session, suffix="_tm")

    item_bud = await _seed_item(db_session, topic="budgeting", answer_index=0)
    item_sav = await _seed_item(db_session, topic="savings", answer_index=2)
    diag = await _create_session(db_session, user, [item_bud, item_sav])

    answers = {str(item_bud.id): 0, str(item_sav.id): 2}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    # TopicMastery rows should exist for budgeting and savings
    bud_mastery = await db_session.get(TopicMastery, (user.id, "budgeting"))
    sav_mastery = await db_session.get(TopicMastery, (user.id, "savings"))

    assert bud_mastery is not None
    assert sav_mastery is not None
    # Both were answered correctly → quizzes_correct == quizzes_attempted == 1
    assert bud_mastery.quizzes_attempted == 1
    assert bud_mastery.quizzes_correct == 1
    assert sav_mastery.quizzes_attempted == 1
    assert sav_mastery.quizzes_correct == 1


# ---------------------------------------------------------------------------
# Another user's session → 403/404
# ---------------------------------------------------------------------------


async def test_submit_other_users_session_forbidden(client, db_session):
    """Submitting a session belonging to another user → 403 or 404."""
    # Create victim user's session without logging in as them
    victim_email = "victim_subm@example.com"
    victim = User(
        email=victim_email,
        username="victimsubm",
        password_hash="x",
        dob=datetime(2012, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(victim)
    await db_session.flush()

    item = await _seed_item(db_session, topic="budgeting")
    victim_session = await _create_session(db_session, victim, [item])

    # Log in as a different user (attacker)
    await _register_and_login(client, db_session, suffix="_atk")

    resp = await client.post(
        "/diagnostic/submit",
        json={"session_id": str(victim_session.id), "answers": {}},
    )
    assert resp.status_code in (403, 404), f"Expected 403/404, got {resp.status_code}"


# ---------------------------------------------------------------------------
# Already-completed session → 409
# ---------------------------------------------------------------------------


async def test_submit_already_completed_session_409(client, db_session):
    """Submitting an already-completed session → 409."""
    user = await _register_and_login(client, db_session, suffix="_dup")

    item = await _seed_item(db_session, topic="budgeting", answer_index=0)
    diag = DiagnosticSession(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind="baseline",
        item_ids=[str(item.id)],
        completed_at=datetime.now(UTC),  # already completed
    )
    db_session.add(diag)
    await db_session.flush()

    resp = await client.post(
        "/diagnostic/submit",
        json={"session_id": str(diag.id), "answers": {str(item.id): 0}},
    )
    assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"


# ---------------------------------------------------------------------------
# NO XP/streak/coins side-effect
# ---------------------------------------------------------------------------


async def test_submit_no_reward_side_effects(client, db_session):
    """Submit must not alter XP, streak, or coins."""
    user = await _register_and_login(client, db_session, suffix="_norew")

    item1 = await _seed_item(db_session, topic="budgeting", answer_index=0)
    item2 = await _seed_item(db_session, topic="savings", answer_index=1)
    diag = await _create_session(db_session, user, [item1, item2])

    progress_before = await _get_progress(client)

    answers = {str(item1.id): 0, str(item2.id): 1}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    progress_after = await _get_progress(client)

    assert progress_after["xp"] == progress_before["xp"], "XP must not change on diagnostic submit"
    assert progress_after["streak_count"] == progress_before["streak_count"], "Streak must not change"
    assert progress_after["virtual_coins"] == progress_before["virtual_coins"], "Coins must not change"


# ---------------------------------------------------------------------------
# Unanswered items count as attempted-incorrect
# ---------------------------------------------------------------------------


async def test_unanswered_items_count_as_incorrect(client, db_session):
    """Items with no answer in the answers dict count as attempted-and-incorrect."""
    user = await _register_and_login(client, db_session, suffix="_unans")

    item1 = await _seed_item(db_session, topic="budgeting", answer_index=0)
    item2 = await _seed_item(db_session, topic="budgeting", answer_index=1)
    diag = await _create_session(db_session, user, [item1, item2])

    # Answer only item1 correctly; leave item2 unanswered
    answers = {str(item1.id): 0}
    resp = await client.post("/diagnostic/submit", json={"session_id": str(diag.id), "answers": answers})
    assert resp.status_code == 200, resp.text

    data = resp.json()
    # 1 correct out of 2 attempted (denominator = session size)
    assert data["overall_score"] == pytest.approx(0.5)
    topics = {t["topic"]: t for t in data["topics"]}
    assert topics["budgeting"]["attempted"] == 2
    assert topics["budgeting"]["correct"] == 1
