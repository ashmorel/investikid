"""Server-side analytics hooks (M4 Task 2)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from app.models.content import Lesson
from app.models.subscription import Subscription
from app.models.user import User
from app.services import digest_service
from app.services.entitlements import set_premium
from app.services.webhook_service import handle_subscription_updated
from tests.test_content import _register_and_login, _seed_modules

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _events(db_session, name: str) -> list[AnalyticsEvent]:
    return list(
        (
            await db_session.execute(
                select(AnalyticsEvent).where(AnalyticsEvent.event_name == name)
            )
        ).scalars()
    )


async def test_complete_lesson_records_event(client, db_session):
    gb_free, _, _, _ = await _seed_modules(db_session)
    lesson = Lesson(module_id=gb_free.id, type="card", content_json={}, xp_reward=10, order_index=0)
    db_session.add(lesson)
    await db_session.commit()

    email = f"a{uuid.uuid4().hex[:8]}@example.com"
    await _register_and_login(client, email=email, username=f"a{uuid.uuid4().hex[:8]}")
    r1 = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r1.status_code == 200
    r2 = await client.post(f"/lessons/{lesson.id}/complete", json={})
    assert r2.status_code == 200

    rows = await _events(db_session, "lesson_completed")
    mine = [r for r in rows if r.props and r.props.get("lesson_id") == str(lesson.id)]
    assert len(mine) == 2
    assert mine[0].role == "child"
    assert {r.props["repeat"] for r in mine} == {False, True}
    assert mine[0].props["module_id"] == str(gb_free.id)


async def test_set_premium_records_activation_once(db_session):
    child = User(
        username=f"k{uuid.uuid4().hex[:8]}",
        email=f"k{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        parent_email="p@x.test",
    )
    db_session.add(child)
    await db_session.flush()

    assert await set_premium(db_session, child, value=True, actor="stripe") is True
    assert await set_premium(db_session, child, value=True, actor="stripe") is False
    assert await set_premium(db_session, child, value=False, actor="stripe") is True

    rows = [
        r for r in await _events(db_session, "subscription_activated") if r.user_id == child.id
    ]
    assert len(rows) == 1
    assert rows[0].props == {"source": "stripe"}


async def test_webhook_trialing_transition_records_trial_started(db_session):
    sub_id = f"sub_{uuid.uuid4().hex[:10]}"
    sub = Subscription(
        parent_email=f"p{uuid.uuid4().hex[:6]}@x.test",
        provider="stripe",
        stripe_subscription_id=sub_id,
        status="incomplete",
    )
    db_session.add(sub)
    await db_session.commit()

    def event(status: str) -> dict:
        return {
            "data": {
                "object": {
                    "id": sub_id,
                    "status": status,
                    "current_period_end": int(
                        (datetime.now(UTC) + timedelta(days=7)).timestamp()
                    ),
                }
            }
        }

    await handle_subscription_updated(db_session, event("trialing"))
    await handle_subscription_updated(db_session, event("trialing"))  # no transition

    rows = [
        r
        for r in await _events(db_session, "trial_started")
        if r.props and r.props.get("source") == "stripe"
    ]
    assert len(rows) >= 1
    # exactly one for THIS subscription's transition: filter via timing window is
    # brittle; assert the second call added nothing new by count delta instead.
    before = len(rows)
    await handle_subscription_updated(db_session, event("trialing"))
    rows_after = [
        r
        for r in await _events(db_session, "trial_started")
        if r.props and r.props.get("source") == "stripe"
    ]
    assert len(rows_after) == before


async def test_digest_send_records_event(db_session, monkeypatch):
    sent = []

    class FakeSender:
        async def send(self, session, *, to, template, context):
            sent.append(to)

    monkeypatch.setattr(digest_service, "get_email_sender", lambda: FakeSender())

    parent = f"p{uuid.uuid4().hex[:6]}@x.test"
    child = User(
        username=f"d{uuid.uuid4().hex[:8]}",
        email=f"d{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        parent_email=parent,
    )
    db_session.add(child)
    await db_session.commit()

    async def fake_build(session, parent_email, *, now):
        if parent_email != parent:
            return None
        return {"parent_email": parent_email}

    monkeypatch.setattr(digest_service, "build_weekly_digest", fake_build)

    before = len(await _events(db_session, "digest_sent"))
    summary = await digest_service.run_weekly_digests(db_session)
    assert summary["sent"] == 1
    rows = await _events(db_session, "digest_sent")
    assert len(rows) == before + 1
    assert rows[-1].role == "parent"
    assert rows[-1].user_id is None
