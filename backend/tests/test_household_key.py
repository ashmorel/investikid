from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.subscription import Subscription
from app.models.user import User
from app.services.entitlements import household_key, recompute_household_premium

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_household_key_prefers_parent_email():
    u = User(username="hk1", password_hash="x", dob=date(2014, 1, 1),
             country_code="GB", currency_code="GBP",
             parent_email="P@Example.com", email="kid@example.com")
    assert household_key(u) == "p@example.com"  # lowercased parent email


def test_household_key_falls_back_to_own_email_for_teen():
    teen = User(username="hk2", password_hash="x", dob=date(2009, 1, 1),
                country_code="GB", currency_code="GBP",
                parent_email=None, email="Teen@Example.com")
    assert household_key(teen) == "teen@example.com"


async def test_recompute_grants_teen_their_self_household(db_session):
    teen = User(username="teenbuyer", password_hash="x", dob=date(2009, 1, 1),
                country_code="GB", currency_code="GBP",
                parent_email=None, email="teenbuyer@example.com")
    db_session.add(teen)
    key = "teenbuyer@example.com"
    db_session.add(Subscription(
        parent_email=key, provider="apple", external_id="otid_teen",
        status="active", current_period_end=datetime.now(UTC) + timedelta(days=30),
    ))
    await db_session.flush()
    await recompute_household_premium(db_session, key)
    assert teen.is_premium is True


async def test_recompute_normal_parent_household_unaffected(db_session):
    # A normal parent household still works and a null-parent_email user whose
    # email does NOT equal the key is NOT granted.
    child = User(username="normalkid", password_hash="x", dob=date(2015, 1, 1),
                 country_code="GB", currency_code="GBP",
                 parent_email="parent-normal@example.com", email=None)
    bystander = User(username="bystander", password_hash="x", dob=date(2009, 1, 1),
                     country_code="GB", currency_code="GBP",
                     parent_email=None, email="bystander@example.com")
    db_session.add_all([child, bystander])
    db_session.add(Subscription(
        parent_email="parent-normal@example.com", provider="stripe",
        external_id="sub_normal", status="active",
        current_period_end=datetime.now(UTC) + timedelta(days=30),
    ))
    await db_session.flush()
    await recompute_household_premium(db_session, "parent-normal@example.com")
    assert child.is_premium is True
    assert bystander.is_premium is False
