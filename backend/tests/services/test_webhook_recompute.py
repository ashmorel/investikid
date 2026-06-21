from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import is_premium
from app.services.webhook_service import (
    handle_checkout_completed,
    handle_subscription_deleted,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _child(db_session, email):
    u = User(
        username=f"kid-{email}",
        email=f"kid-{email}",
        parent_email=email,
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
    )
    db_session.add(u)
    await db_session.flush()
    return u


async def test_subscription_deleted_revokes_via_recompute(db_session):
    email = "del-recompute@example.com"
    child = await _child(db_session, email)
    child.is_premium = True
    db_session.add(
        Subscription(
            parent_email=email,
            provider="stripe",
            external_id="sub_del_rc",
            stripe_subscription_id="sub_del_rc",
            status="active",
        )
    )
    await db_session.flush()

    event = {"data": {"object": {"id": "sub_del_rc"}}}
    await handle_subscription_deleted(db_session, event)

    assert is_premium(child) is False
    # Audit attribution comes from recompute, not the old "stripe" actor.
    audit = await db_session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == child.id, AuditLog.event_type == "premium_revoke")
        .order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.metadata_json["actor"] == "billing:recompute"


async def test_checkout_completed_grants_and_sets_provider(db_session):
    email = "ckout-recompute@example.com"
    child = await _child(db_session, email)
    db_session.add(
        Subscription(
            parent_email=email,
            stripe_customer_id="cus_rc",
            status="incomplete",
        )
    )
    await db_session.flush()

    event = {
        "data": {
            "object": {
                "customer": "cus_rc",
                "subscription": "sub_rc",
                "metadata": {"parent_email": email},
            }
        }
    }
    stripe_sub = SimpleNamespace(
        status="active",
        current_period_end=int((datetime.now(UTC) + timedelta(days=30)).timestamp()),
        cancel_at_period_end=False,
    )
    with patch(
        "app.services.webhook_service.stripe.Subscription.retrieve",
        return_value=stripe_sub,
    ):
        await handle_checkout_completed(db_session, event)

    assert is_premium(child) is True

    sub = await db_session.scalar(
        select(Subscription).where(Subscription.stripe_customer_id == "cus_rc")
    )
    assert sub.provider == "stripe"
    assert sub.external_id == "sub_rc"
    assert sub.status == "active"

    audit = await db_session.scalar(
        select(AuditLog)
        .where(AuditLog.user_id == child.id, AuditLog.event_type == "premium_grant")
        .order_by(AuditLog.created_at.desc())
    )
    assert audit is not None
    assert audit.metadata_json["actor"] == "billing:recompute"
