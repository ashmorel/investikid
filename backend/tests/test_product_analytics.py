"""Unit tests for the analytics record() seam (M4)."""
import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.services import product_analytics_service as analytics_service

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_child(db_session, *, dob: date, is_premium: bool = False) -> User:
    user = User(
        username=f"kid{uuid.uuid4().hex[:8]}",
        email=f"kid-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        dob=dob,
        country_code="US",
        currency_code="USD",
        is_premium=is_premium,
        parent_email="p@x.test",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_record_writes_row_with_snapshots(db_session):
    child = await _make_child(db_session, dob=date(2010, 1, 1), is_premium=True)
    await analytics_service.record(
        db_session,
        "lesson_completed",
        user=child,
        role="child",
        props={"module_id": "m1", "repeat": False},
    )
    await db_session.flush()
    row = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.user_id == child.id)
        )
    ).scalar_one()
    assert row.event_name == "lesson_completed"
    assert row.role == "child"
    assert row.age_tier == "investor"  # born 2010 -> 16 in 2026
    assert row.is_premium is True
    assert row.props == {"module_id": "m1", "repeat": False}
    assert row.occurred_at.tzinfo is not None


async def test_record_filters_disallowed_prop_keys(db_session):
    child = await _make_child(db_session, dob=date(2015, 6, 1))
    await analytics_service.record(
        db_session,
        "lesson_completed",
        user=child,
        role="child",
        props={"module_id": "m1", "email": "leak@example.com", "note": "x" * 500},
    )
    await db_session.flush()
    row = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.user_id == child.id)
        )
    ).scalar_one()
    assert row.props == {"module_id": "m1"}
    assert row.age_tier == "explorer"


async def test_record_unknown_event_name_is_dropped(db_session):
    child = await _make_child(db_session, dob=date(2014, 1, 1))
    await analytics_service.record(db_session, "made_up_event", user=child, role="child")
    await db_session.flush()
    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.user_id == child.id)
        )
    ).scalars().all()
    assert rows == []


async def test_record_never_raises(db_session):
    class Boom:
        def add(self, *_a, **_k):  # noqa: ANN002, ANN003
            raise RuntimeError("db down")

    # Must swallow, not raise into the caller.
    await analytics_service.record(Boom(), "lesson_completed", user=None, role="child")


async def test_record_without_user(db_session):
    marker = uuid.uuid4().hex[:8]
    await analytics_service.record(
        db_session, "digest_sent", user=None, role="parent", props={"surface": marker}
    )
    await db_session.flush()
    row = (
        await db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name == "digest_sent",
                AnalyticsEvent.props["surface"].as_string() == marker,
            )
        )
    ).scalar_one()
    assert row.user_id is None
    assert row.age_tier is None
    assert row.is_premium is None


async def test_purge_old_events(db_session):
    old = AnalyticsEvent(
        event_name="home_view",
        role="child",
        occurred_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    new = AnalyticsEvent(
        event_name="home_view",
        role="child",
        occurred_at=datetime.now(UTC),
    )
    db_session.add_all([old, new])
    await db_session.flush()
    deleted = await analytics_service.purge_old_events(db_session, now=datetime.now(UTC))
    assert deleted >= 1
    remaining = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.id.in_([old.id, new.id]))
        )
    ).scalars().all()
    assert [r.id for r in remaining] == [new.id]
