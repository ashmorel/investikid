from datetime import date

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _dob_for_age(age: int) -> str:
    today = date.today()
    return date(today.year - age, today.month, today.day).isoformat()


async def test_over_threshold_teen_registers_without_parent_email(client):
    # GB consent age is 13; a 15yo is self-managed and needs only their own email.
    resp = await client.post("/auth/register", json={
        "email": "teen-selfmanaged@example.com", "username": "teenself",
        "password": "SecurePass123!", "dob": _dob_for_age(15),
        "country_code": "GB", "currency_code": "GBP",
    })
    # Register's success contract is 201 Created (see test_auth.py); the consent
    # branch under test is that an over-threshold teen succeeds with no parent email.
    assert resp.status_code == 201, resp.text


async def test_under_threshold_child_requires_parent_email(client):
    # GB consent age is 13; a 9yo MUST have a parent email.
    resp = await client.post("/auth/register", json={
        "username": "younglearner", "password": "SecurePass123!",
        "dob": _dob_for_age(9), "country_code": "GB", "currency_code": "GBP",
    })
    assert resp.status_code == 400


async def test_under_threshold_child_succeeds_with_parent_email(client):
    resp = await client.post("/auth/register", json={
        "username": "younglearner2", "password": "SecurePass123!",
        "dob": _dob_for_age(9), "country_code": "GB", "currency_code": "GBP",
        "parent_email": "guardian@example.com",
    })
    # 201 = consent flow accepted; body is { status: pending_consent } until the
    # parent approves. The branch under test is that supplying parent_email is accepted.
    assert resp.status_code == 201, resp.text
