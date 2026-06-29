"""TDD tests for MasteryCheckpoint, MasteryCheckpointTopic, DiagnosticSession models.

Run first (red), then implement models + migration, then run again (green).
"""
import datetime as dt
import uuid

import pytest
from sqlalchemy import select

from app.models.mastery import DiagnosticSession, MasteryCheckpoint, MasteryCheckpointTopic
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _user() -> User:
    return User(
        username=f"m{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@mastery.test",
        password_hash="x",
        dob=dt.date(2015, 6, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@mastery.test",
    )


async def test_mastery_checkpoint_defaults(db_session):
    """MasteryCheckpoint persists with correct defaults for session_count, overall_score, taken_at."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    cp = MasteryCheckpoint(
        user_id=user.id,
        market_code="GB",
        kind="baseline",
    )
    db_session.add(cp)
    await db_session.flush()
    await db_session.refresh(cp)

    assert cp.id is not None
    assert cp.session_count == 0
    assert cp.overall_score is None
    assert cp.taken_at is not None
    assert cp.kind == "baseline"
    assert cp.market_code == "GB"


async def test_mastery_checkpoint_with_score(db_session):
    """MasteryCheckpoint stores a fractional overall_score correctly."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    cp = MasteryCheckpoint(
        user_id=user.id,
        market_code="US",
        kind="progress",
        session_count=3,
        overall_score=0.72,
    )
    db_session.add(cp)
    await db_session.flush()
    await db_session.refresh(cp)

    assert cp.overall_score == pytest.approx(0.72)
    assert cp.session_count == 3
    assert cp.kind == "progress"


async def test_mastery_checkpoint_topic_rows(db_session):
    """MasteryCheckpointTopic rows persist with correct fields."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    cp = MasteryCheckpoint(user_id=user.id, market_code="GB", kind="baseline")
    db_session.add(cp)
    await db_session.flush()

    t1 = MasteryCheckpointTopic(
        checkpoint_id=cp.id, topic="stocks", correct=4, attempted=5
    )
    t2 = MasteryCheckpointTopic(
        checkpoint_id=cp.id, topic="savings", correct=2, attempted=4
    )
    db_session.add_all([t1, t2])
    await db_session.flush()

    rows = (
        await db_session.execute(
            select(MasteryCheckpointTopic).where(
                MasteryCheckpointTopic.checkpoint_id == cp.id
            )
        )
    ).scalars().all()

    assert len(rows) == 2
    topics = {r.topic: r for r in rows}
    assert topics["stocks"].correct == 4
    assert topics["stocks"].attempted == 5
    assert topics["savings"].correct == 2


async def test_cascade_delete_checkpoint_removes_topics(db_session):
    """Deleting a MasteryCheckpoint cascades and removes its topic rows."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    cp = MasteryCheckpoint(user_id=user.id, market_code="GB", kind="skipped")
    db_session.add(cp)
    await db_session.flush()

    cp_id = cp.id
    t = MasteryCheckpointTopic(checkpoint_id=cp_id, topic="debt", correct=1, attempted=3)
    db_session.add(t)
    await db_session.flush()

    # verify topic exists
    count_before = (
        await db_session.execute(
            select(MasteryCheckpointTopic).where(
                MasteryCheckpointTopic.checkpoint_id == cp_id
            )
        )
    ).scalars().all()
    assert len(count_before) == 1

    # delete checkpoint — cascade should remove topic
    await db_session.delete(cp)
    await db_session.flush()

    count_after = (
        await db_session.execute(
            select(MasteryCheckpointTopic).where(
                MasteryCheckpointTopic.checkpoint_id == cp_id
            )
        )
    ).scalars().all()
    assert len(count_after) == 0


async def test_diagnostic_session_defaults(db_session):
    """DiagnosticSession persists with correct defaults for completed_at."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    session = DiagnosticSession(
        user_id=user.id,
        market_code="US",
        kind="baseline",
        item_ids=["item-1", "item-2", "item-3"],
    )
    db_session.add(session)
    await db_session.flush()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.completed_at is None
    assert session.created_at is not None
    assert session.kind == "baseline"
    assert session.market_code == "US"


async def test_diagnostic_session_item_ids_roundtrip(db_session):
    """DiagnosticSession.item_ids round-trips a list of strings through JSON."""
    user = _user()
    db_session.add(user)
    await db_session.flush()

    ids = ["abc-123", "def-456", "ghi-789"]
    session = DiagnosticSession(
        user_id=user.id,
        market_code="GB",
        kind="progress",
        item_ids=ids,
    )
    db_session.add(session)
    await db_session.flush()

    fetched = await db_session.scalar(
        select(DiagnosticSession).where(DiagnosticSession.id == session.id)
    )
    assert fetched is not None
    assert fetched.item_ids == ids
