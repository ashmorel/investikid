from datetime import date

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import is_premium, recompute_household_premium

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


async def test_grants_when_any_active(db_session):
    email = "a@example.com"
    child = await _child(db_session, email)
    db_session.add(
        Subscription(parent_email=email, provider="apple", external_id="t1", status="active")
    )
    await db_session.flush()
    await recompute_household_premium(db_session, email)
    assert is_premium(child) is True


async def test_revokes_when_none_active(db_session):
    email = "b@example.com"
    child = await _child(db_session, email)
    child.is_premium = True
    db_session.add(
        Subscription(parent_email=email, provider="apple", external_id="t2", status="expired")
    )
    await db_session.flush()
    await recompute_household_premium(db_session, email)
    assert is_premium(child) is False


async def test_trialing_and_grace_count_as_active(db_session):
    for email, st in (("c@example.com", "trialing"), ("d@example.com", "in_grace_period")):
        child = await _child(db_session, email)
        db_session.add(
            Subscription(parent_email=email, provider="apple", external_id=f"t-{st}", status=st)
        )
        await db_session.flush()
        await recompute_household_premium(db_session, email)
        assert is_premium(child) is True
