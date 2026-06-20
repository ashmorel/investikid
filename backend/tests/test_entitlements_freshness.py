from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import recompute_household_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed(db_session, *, parent: str, username: str, status: str, period_end):
    # Start premium so the expired-period test proves the guard REVOKES it
    # (a child defaulting to non-premium would pass even without the guard).
    child = User(username=username, password_hash="x", dob=date(2014, 1, 1),
                 country_code="GB", currency_code="GBP", parent_email=parent,
                 is_premium=True)
    db_session.add(child)
    db_session.add(Subscription(
        parent_email=parent, provider="stripe", external_id=f"sub_{username}",
        status=status, current_period_end=period_end,
    ))
    await db_session.flush()
    return child


async def test_expired_active_row_does_not_entitle(db_session):
    p = "fresh-expired@example.com"
    child = await _seed(db_session, parent=p, username="fresh-exp",
                        status="active", period_end=datetime.now(UTC) - timedelta(days=1))
    await recompute_household_premium(db_session, p)
    assert child.is_premium is False


async def test_future_period_entitles(db_session):
    p = "fresh-future@example.com"
    child = await _seed(db_session, parent=p, username="fresh-fut",
                        status="active", period_end=datetime.now(UTC) + timedelta(days=10))
    await recompute_household_premium(db_session, p)
    assert child.is_premium is True


async def test_null_period_still_entitles(db_session):
    p = "fresh-null@example.com"
    child = await _seed(db_session, parent=p, username="fresh-null",
                        status="active", period_end=None)
    await recompute_household_premium(db_session, p)
    assert child.is_premium is True
