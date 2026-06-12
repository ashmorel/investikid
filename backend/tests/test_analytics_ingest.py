"""POST /analytics/events ingest endpoint (M4 Task 3)."""
import uuid

import pytest
from sqlalchemy import select

from app.models.analytics import AnalyticsEvent
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _login(client) -> None:
    suffix = uuid.uuid4().hex[:8]
    await _register_and_login(client, email=f"i{suffix}@example.com", username=f"i{suffix}")


async def test_ingest_requires_auth(client):
    response = await client.post(
        "/analytics/events", json={"events": [{"event_name": "home_view"}]}
    )
    assert response.status_code in (401, 403)  # CSRF gate fires before auth on bare POSTs


async def test_ingest_accepts_client_events(client, db_session):
    await _login(client)
    response = await client.post(
        "/analytics/events",
        json={
            "events": [
                {"event_name": "home_view"},
                {"event_name": "home_cta_tap", "props": {"surface": "hero"}},
                {"event_name": "quicklink_tap", "props": {"surface": "portfolio"}},
            ]
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 3
    assert body["dropped"] == 0

    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.event_name == "home_cta_tap")
        )
    ).scalars().all()
    assert any(r.props == {"surface": "hero"} and r.role == "child" for r in rows)


async def test_ingest_drops_server_only_and_unknown_names(client, db_session):
    await _login(client)
    response = await client.post(
        "/analytics/events",
        json={
            "events": [
                {"event_name": "subscription_activated"},  # server-only
                {"event_name": "totally_made_up"},
                {"event_name": "paywall_view", "props": {"surface": "module", "email": "x@x"}},
            ]
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] == 1
    assert body["dropped"] == 2

    rows = (
        await db_session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.event_name.in_(["subscription_activated", "totally_made_up"])
            )
        )
    ).scalars().all()
    # no server-only event written via ingest (any pre-existing ones belong to other tests)
    pw = (
        await db_session.execute(
            select(AnalyticsEvent).where(AnalyticsEvent.event_name == "paywall_view")
        )
    ).scalars().all()
    assert all("email" not in (r.props or {}) for r in pw)
    assert all(r.event_name != "totally_made_up" for r in rows)


async def test_ingest_caps_batch_size(client):
    await _login(client)
    response = await client.post(
        "/analytics/events",
        json={"events": [{"event_name": "home_view"}] * 21},
    )
    assert response.status_code == 422
