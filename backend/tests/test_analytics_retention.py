"""Analytics retention: internal cron endpoint, purge hook, import-surface pin (M4 Task 4)."""
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.services import product_analytics_service
from app.services.retention import purge_expired_accounts

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/internal/analytics-retention/run"


async def test_endpoint_guards(client, monkeypatch):
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", "")
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "x"})).status_code == 503
    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    assert (await client.post(_PATH)).status_code == 401
    assert (await client.post(_PATH, headers={"X-Cron-Secret": "nope"})).status_code == 401


async def test_endpoint_deletes_old_events(client, db_session, monkeypatch):
    import app.routers.internal as internal

    monkeypatch.setattr(internal.settings, "cron_secret", "s3cr3t")
    old = AnalyticsEvent(
        event_name="home_view", role="child",
        occurred_at=datetime.now(UTC) - timedelta(days=500),
    )
    db_session.add(old)
    await db_session.commit()

    r = await client.post(_PATH, headers={"X-Cron-Secret": "s3cr3t"})
    assert r.status_code == 200
    assert r.json()["deleted"] >= 1

    gone = await db_session.get(AnalyticsEvent, old.id)
    assert gone is None or (await db_session.refresh(gone)) is None  # row deleted


async def test_account_purge_nulls_analytics_user_id(db_session):
    child = User(
        username=f"r{uuid.uuid4().hex[:8]}",
        email=f"r{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=date(2014, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="p@x.test",
    )
    db_session.add(child)
    await db_session.flush()
    await product_analytics_service.record(
        db_session, "lesson_completed", user=child, role="child"
    )
    await db_session.flush()
    child_id = child.id

    child.deleted_at = datetime.now(UTC) - timedelta(days=400)
    await db_session.commit()

    purged = await purge_expired_accounts(db_session, date.today())
    assert purged >= 1

    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.user_id == child_id)
        )
    ).scalars().all()
    assert rows == []


def test_analytics_model_import_surface_is_pinned():
    """The AnalyticsEvent model must never leak into personalization paths.

    Allowed importers: the product analytics service, the admin analytics
    surface, the models package registry, and migrations/tests.
    """
    app_dir = Path(__file__).resolve().parents[1] / "app"
    allowed = {
        "services/product_analytics_service.py",
        "routers/admin_analytics.py",
        "models/__init__.py",
    }
    offenders = []
    for py in app_dir.rglob("*.py"):
        rel = py.relative_to(app_dir).as_posix()
        if rel in allowed or rel == "models/analytics.py":
            continue
        text = py.read_text()
        if re.search(r"from app\.models\.analytics import|models\.analytics", text):
            offenders.append(rel)
    assert offenders == []
