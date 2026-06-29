"""Tests for GET /diagnostic/evidence (Task 4 — read-only aggregation).

TDD: tests written first, run → fail, then implementation lands.

Coverage:
- no checkpoints → has_baseline == false
- baseline only → baseline present, latest null, topic_deltas empty
- baseline + later progress → correct per-topic deltas + overall_delta
- skipped baseline → has_baseline true, baseline_skipped true, no scores
- unknown-topic row is excluded from evidence output
- unauth → 401
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.mastery import MasteryCheckpoint, MasteryCheckpointTopic
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

_DEFAULT_MARKET = "GB"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(client, email: str, password: str) -> None:
    await client.post("/auth/login", json={"email": email, "password": password})
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


async def _register_and_login(client, db_session, *, suffix: str = "") -> User:
    """Register a new user, log them in, return the ORM User row."""
    email = f"evid{suffix}@example.com"
    username = f"evidkid{suffix}"
    payload = {
        "email": email,
        "username": username,
        "password": "SecurePass123!",
        "dob": "2012-01-01",
        "country_code": "GB",
        "currency_code": "GBP",
        "parent_email": f"evid_parent{suffix}@example.com",
    }
    await client.post("/auth/register", json=payload)
    await _login(client, email, "SecurePass123!")
    return await db_session.scalar(select(User).where(User.username == username))


async def _make_checkpoint(
    db_session,
    user: User,
    *,
    kind: str,
    overall_score: float | None = None,
    session_count: int = 0,
    taken_at: datetime | None = None,
    topics: list[tuple[str, int, int]] | None = None,
) -> MasteryCheckpoint:
    """Create a MasteryCheckpoint with optional topic rows.

    topics: list of (topic, correct, attempted)
    """
    cp = MasteryCheckpoint(
        user_id=user.id,
        market_code=_DEFAULT_MARKET,
        kind=kind,
        overall_score=overall_score,
        session_count=session_count,
        taken_at=taken_at or datetime.now(UTC),
    )
    db_session.add(cp)
    await db_session.flush()

    for topic, correct, attempted in (topics or []):
        db_session.add(
            MasteryCheckpointTopic(
                checkpoint_id=cp.id,
                topic=topic,
                correct=correct,
                attempted=attempted,
            )
        )
    await db_session.flush()
    return cp


# ---------------------------------------------------------------------------
# no checkpoints → has_baseline == false
# ---------------------------------------------------------------------------


async def test_no_checkpoints_returns_no_baseline(client, db_session):
    """User with no checkpoints → has_baseline=false, baseline=null."""
    await _register_and_login(client, db_session, suffix="_nocp")

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["has_baseline"] is False
    assert data["baseline"] is None
    assert data["latest"] is None
    assert data["overall_delta"] is None
    assert data["topic_deltas"] == []


# ---------------------------------------------------------------------------
# baseline only → baseline present, latest null, topic_deltas empty
# ---------------------------------------------------------------------------


async def test_baseline_only_no_delta(client, db_session):
    """Baseline checkpoint only → baseline present, latest null, no deltas."""
    user = await _register_and_login(client, db_session, suffix="_bo")

    await _make_checkpoint(
        db_session,
        user,
        kind="baseline",
        overall_score=0.6,
        session_count=5,
        topics=[("budgeting", 3, 5), ("savings", 2, 5)],
    )

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["has_baseline"] is True
    assert data["baseline_skipped"] is False
    assert data["baseline"]["overall_score"] == pytest.approx(0.6)
    assert data["baseline"]["session_count"] == 5

    baseline_topics = {t["topic"]: t for t in data["baseline"]["topics"]}
    assert "budgeting" in baseline_topics
    assert baseline_topics["budgeting"]["score"] == pytest.approx(3 / 5)
    assert "savings" in baseline_topics
    assert baseline_topics["savings"]["score"] == pytest.approx(2 / 5)

    # No progress yet
    assert data["latest"] is None
    assert data["overall_delta"] is None
    assert data["topic_deltas"] == []


# ---------------------------------------------------------------------------
# baseline + later progress → correct per-topic deltas + overall_delta
# ---------------------------------------------------------------------------


async def test_baseline_plus_progress_deltas(client, db_session):
    """Baseline + progress checkpoint → correct per-topic + overall deltas."""
    from datetime import timedelta

    user = await _register_and_login(client, db_session, suffix="_bp")

    base_time = datetime(2026, 1, 1, tzinfo=UTC)
    prog_time = base_time + timedelta(days=30)

    await _make_checkpoint(
        db_session,
        user,
        kind="baseline",
        overall_score=0.4,
        session_count=5,
        taken_at=base_time,
        topics=[("budgeting", 2, 5), ("savings", 1, 5)],
    )
    await _make_checkpoint(
        db_session,
        user,
        kind="progress",
        overall_score=0.8,
        session_count=10,
        taken_at=prog_time,
        topics=[("budgeting", 4, 5), ("savings", 4, 5)],
    )

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["has_baseline"] is True
    assert data["baseline_skipped"] is False

    assert data["baseline"]["overall_score"] == pytest.approx(0.4)
    assert data["latest"]["overall_score"] == pytest.approx(0.8)
    assert data["latest"]["session_count"] == 10

    # overall_delta
    assert data["overall_delta"] == pytest.approx(0.8 - 0.4)

    # per-topic deltas
    deltas = {d["topic"]: d for d in data["topic_deltas"]}
    assert "budgeting" in deltas
    assert deltas["budgeting"]["baseline_score"] == pytest.approx(2 / 5)
    assert deltas["budgeting"]["latest_score"] == pytest.approx(4 / 5)
    assert deltas["budgeting"]["delta"] == pytest.approx(4 / 5 - 2 / 5)

    assert "savings" in deltas
    assert deltas["savings"]["delta"] == pytest.approx(4 / 5 - 1 / 5)

    # session_count is from latest
    assert data["session_count"] == 10


# ---------------------------------------------------------------------------
# skipped baseline → has_baseline true, baseline_skipped true, no scores
# ---------------------------------------------------------------------------


async def test_skipped_baseline(client, db_session):
    """A skipped baseline → baseline_skipped=true, no scores."""
    user = await _register_and_login(client, db_session, suffix="_sk")

    await _make_checkpoint(
        db_session,
        user,
        kind="skipped",
        overall_score=None,
        session_count=0,
    )

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["has_baseline"] is True
    assert data["baseline_skipped"] is True
    # No scores
    assert data["baseline"] is None
    assert data["latest"] is None
    assert data["overall_delta"] is None
    assert data["topic_deltas"] == []


# ---------------------------------------------------------------------------
# unknown-topic row excluded from evidence output
# ---------------------------------------------------------------------------


async def test_unknown_topic_excluded(client, db_session):
    """A topic=='unknown' row must be filtered out and not appear in evidence."""
    user = await _register_and_login(client, db_session, suffix="_unk")

    await _make_checkpoint(
        db_session,
        user,
        kind="baseline",
        overall_score=0.5,
        session_count=3,
        topics=[("budgeting", 2, 4), ("unknown", 1, 2)],
    )

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["has_baseline"] is True
    baseline_topics = {t["topic"]: t for t in data["baseline"]["topics"]}
    assert "unknown" not in baseline_topics
    assert "budgeting" in baseline_topics


# ---------------------------------------------------------------------------
# unauth → 401
# ---------------------------------------------------------------------------


async def test_evidence_unauthenticated(client, db_session):
    """Unauthenticated request → 401."""
    # Ensure no auth cookies linger
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)

    resp = await client.get("/diagnostic/evidence")
    assert resp.status_code == 401, resp.text
