"""Digest premium-line copy variants (M6 Task 2)."""
import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.services import digest_service
from app.services.email import _premium_line_html, premium_variant

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_variant_is_deterministic_and_covers_all():
    emails = [f"v{i}@example.com" for i in range(60)]
    variants = {premium_variant(e) for e in emails}
    assert variants == {"a", "b", "c"}
    for e in emails:
        assert premium_variant(e) == premium_variant(e.upper())


def test_premium_line_copy_per_variant():
    ctx = {"children": [{"name": "Maya", "masteries": [{"x": 1}, {"x": 2}]}]}
    a = _premium_line_html(ctx, "https://app", "a")
    b = _premium_line_html(ctx, "https://app", "b")
    c = _premium_line_html(ctx, "https://app", "c")
    assert "deeper skills" in a
    assert "mastered 2 skills this week" in b
    assert "full picture" in c
    # b falls back to a-copy on a no-mastery week
    quiet = {"children": [{"name": "Maya", "masteries": []}]}
    assert "deeper skills" in _premium_line_html(quiet, "https://app", "b")


async def test_digest_sent_event_carries_variant(db_session, monkeypatch):
    sent = []

    class FakeSender:
        async def send(self, session, *, to, template, context):
            sent.append(to)

    monkeypatch.setattr(digest_service, "get_email_sender", lambda: FakeSender())
    parent = f"var{uuid.uuid4().hex[:6]}@example.com"
    child = User(
        username=f"v{uuid.uuid4().hex[:8]}",
        email=f"v{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent,
    )
    db_session.add(child)
    await db_session.commit()

    async def fake_build(session, parent_email, *, now):
        return {"parent_email": parent_email} if parent_email == parent else None

    monkeypatch.setattr(digest_service, "build_weekly_digest", fake_build)
    summary = await digest_service.run_weekly_digests(db_session)
    assert summary["sent"] == 1

    row = (
        await db_session.execute(
            select(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == "digest_sent")
            .order_by(AnalyticsEvent.occurred_at.desc())
            .limit(1)
        )
    ).scalar_one()
    assert row.props["variant"] == premium_variant(parent)
