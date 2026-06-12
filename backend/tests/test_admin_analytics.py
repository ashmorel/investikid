"""GET /admin/analytics/summary (M4 Task 5)."""
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.analytics import AnalyticsEvent
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")

_PATH = "/admin/analytics/summary"


def _child(created_at: datetime) -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"s{suffix}",
        email=f"s{suffix}@x.test",
        password_hash="x",
        dob=datetime(2014, 1, 1).date(),
        country_code="GB",
        currency_code="GBP",
        parent_email="p@x.test",
    )
    user.created_at = created_at
    return user


def _event(name: str, *, user_id=None, at: datetime, props=None, role="child") -> AnalyticsEvent:
    return AnalyticsEvent(
        event_name=name, user_id=user_id, role=role, occurred_at=at, props=props
    )


async def test_requires_admin(client):
    assert (await client.get(_PATH)).status_code == 401


async def test_summary_maths(admin_client, db_session):
    now = datetime.now(UTC)

    # Activation: two signups 2 days ago; one completes a lesson within 24h.
    activated = _child(now - timedelta(days=2))
    dormant = _child(now - timedelta(days=2))
    # Cohort: one signup 10 days ago who was active on day 8 (D7 retained).
    retained = _child(now - timedelta(days=10))
    db_session.add_all([activated, dormant, retained])
    await db_session.flush()

    db_session.add_all([
        _event("lesson_completed", user_id=activated.id, at=now - timedelta(days=2) + timedelta(hours=3)),
        _event("lesson_completed", user_id=retained.id, at=now - timedelta(days=2)),  # day 8 after signup
        _event("home_view", user_id=activated.id, at=now - timedelta(hours=5)),
        _event("home_view", user_id=dormant.id, at=now - timedelta(hours=4)),
        _event("home_cta_tap", user_id=activated.id, at=now - timedelta(hours=5), props={"surface": "hero"}),
        _event("quicklink_tap", user_id=activated.id, at=now - timedelta(hours=5), props={"surface": "portfolio"}),
        _event("paywall_view", user_id=dormant.id, at=now - timedelta(hours=3), props={"surface": "module"}),
        _event("trial_started", at=now - timedelta(hours=2), role="parent", props={"source": "stripe"}),
        _event("subscription_activated", user_id=activated.id, at=now - timedelta(hours=1)),
        _event("digest_sent", at=now - timedelta(hours=1), role="parent"),
    ])
    await db_session.commit()

    response = await admin_client.get(_PATH, params={"days": 30})
    assert response.status_code == 200
    body = response.json()

    assert body["window_days"] == 30
    # Exact totals depend on rows other tests in the session created, so assert
    # on the deterministic slice we control where global state could interfere.
    assert body["activation"]["signups"] >= 3
    assert body["activation"]["activated"] >= 1
    assert 0 < body["activation"]["rate_pct"] <= 100

    assert body["funnel"]["paywall_view"] >= 1
    assert body["funnel"]["trial_started"] >= 1
    assert body["funnel"]["subscription_activated"] >= 1

    eng = body["engagement"]
    assert eng["home_view"] >= 2
    assert eng["home_cta_tap"] >= 1
    assert eng["cta_through_pct"] is not None
    assert eng["quicklink_taps"].get("portfolio", 0) >= 1
    assert eng["lesson_completed"] >= 2
    assert eng["digest_sent"] >= 1

    cohorts = body["cohorts"]
    assert isinstance(cohorts, list) and len(cohorts) >= 1
    # The 10-days-ago cohort week exists and shows D7 retention > 0.
    assert any((c["d7_pct"] or 0) > 0 for c in cohorts)


async def test_days_param_validated(admin_client):
    assert (await admin_client.get(_PATH, params={"days": 0})).status_code == 422
    assert (await admin_client.get(_PATH, params={"days": 365})).status_code == 422
