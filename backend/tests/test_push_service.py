"""push_service + streak-risk trigger (M7 Task 5)."""
import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.analytics import AnalyticsEvent
from app.models.push_device import PushDevice
from app.models.user import User, UserProgress
from app.services import push_service, streak_risk_push

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2026, 6, 12)


async def _child_with_device(
    db_session, *, push_enabled=True, streak=5, last_activity=None, dob=date(2014, 1, 1)
):
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"ps{suffix}", email=f"ps{suffix}@example.com", password_hash="x",
        dob=dob, country_code="GB", currency_code="GBP",
        parent_email="p@example.com", push_enabled=push_enabled,
    )
    db_session.add(user)
    await db_session.flush()
    progress = UserProgress(
        user_id=user.id, streak_count=streak,
        last_activity_date=last_activity or (TODAY - timedelta(days=1)),
    )
    device = PushDevice(user_id=user.id, platform="ios", token=f"tok-{suffix}")
    db_session.add_all([progress, device])
    await db_session.commit()
    return user, progress, device


async def test_unconfigured_is_a_noop_and_keeps_cap_unset(db_session, monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account_json", "")
    user, progress, _ = await _child_with_device(db_session)
    sent = await push_service.send_to_user(
        db_session, user.id, kind="streak_risk", title="t", body="b", today=TODAY
    )
    assert sent is False
    assert progress.last_push_sent_date is None


async def test_send_caps_at_one_per_day_and_records_event(db_session, monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account_json", "{}")
    calls = []
    monkeypatch.setattr(push_service, "_send_fcm", lambda tok, t, b: calls.append(tok))

    user, progress, _ = await _child_with_device(db_session)
    before = len((await db_session.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.event_name == "push_sent")
    )).scalars().all())

    assert await push_service.send_to_user(
        db_session, user.id, kind="streak_risk", title="t", body="b", today=TODAY
    ) is True
    assert progress.last_push_sent_date == TODAY
    assert len(calls) == 1

    # capped on the second attempt the same day
    assert await push_service.send_to_user(
        db_session, user.id, kind="streak_risk", title="t", body="b", today=TODAY
    ) is False
    assert len(calls) == 1

    after = (await db_session.execute(
        select(AnalyticsEvent).where(AnalyticsEvent.event_name == "push_sent")
    )).scalars().all()
    assert len(after) == before + 1
    assert after[-1].props == {"surface": "streak_risk"}


async def test_dead_token_is_pruned(db_session, monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account_json", "{}")

    class UnregisteredError(Exception):
        pass

    def boom(token, title, body):
        raise UnregisteredError("gone")

    monkeypatch.setattr(push_service, "_send_fcm", boom)
    user, progress, device = await _child_with_device(db_session)
    sent = await push_service.send_to_user(
        db_session, user.id, kind="streak_risk", title="t", body="b", today=TODAY
    )
    assert sent is False
    remaining = await db_session.scalar(
        select(PushDevice).where(PushDevice.id == device.id)
    )
    assert remaining is None


async def test_streak_risk_selection(db_session, monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account_json", "{}")
    sent_tokens = []
    monkeypatch.setattr(push_service, "_send_fcm", lambda tok, t, b: sent_tokens.append((tok, t, b)))

    at_risk, *_ = await _child_with_device(db_session)  # yesterday → in
    await _child_with_device(db_session, last_activity=TODAY)  # active today → out
    await _child_with_device(db_session, streak=0)  # no streak → out
    await _child_with_device(db_session, push_enabled=False)  # parent off → out
    teen, *_ = await _child_with_device(db_session, dob=date(2010, 1, 1))  # investor copy

    summary = await streak_risk_push.run(db_session, today=TODAY)
    assert summary["candidates"] >= 2
    assert summary["sent"] >= 2

    bodies = [b for _, _, b in sent_tokens]
    assert any("🔥" in b for b in bodies)        # explorer copy
    assert any("🔥" not in b and "streak" in b for b in bodies)  # investor copy
