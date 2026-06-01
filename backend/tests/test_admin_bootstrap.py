from datetime import date

import pytest

from app.models.user import User
from app.seed.admin_bootstrap import bootstrap_admin

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user(db_session, email: str) -> User:
    user = User(
        email=email, username=email.split("@")[0], password_hash="x",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_bootstrap_grants_admin_to_matching_email(db_session, monkeypatch):
    user = await _make_user(db_session, "boss@example.com")
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "boss@example.com")
    await bootstrap_admin(db_session)
    assert user.is_admin is True


async def test_bootstrap_is_case_insensitive(db_session, monkeypatch):
    user = await _make_user(db_session, "Mixed@Example.com")
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "mixed@example.com")
    await bootstrap_admin(db_session)
    assert user.is_admin is True


async def test_bootstrap_noop_when_unset(db_session, monkeypatch):
    user = await _make_user(db_session, "nobody@example.com")
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "")
    await bootstrap_admin(db_session)
    assert user.is_admin is False


async def test_bootstrap_matches_by_username(db_session, monkeypatch):
    user = await _make_user(db_session, "someone@example.com")  # username "someone"
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "Someone")
    await bootstrap_admin(db_session)
    assert user.is_admin is True


async def test_bootstrap_ignores_parent_email(db_session, monkeypatch):
    user = await _make_user(db_session, "kid@example.com")
    user.parent_email = "grownup@example.com"
    await db_session.flush()
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "grownup@example.com")
    await bootstrap_admin(db_session)
    assert user.is_admin is False  # parent_email must NOT grant admin


async def test_bootstrap_noop_when_user_missing(db_session, monkeypatch):
    # No user with this email — must not raise.
    monkeypatch.setattr("app.seed.admin_bootstrap.settings.admin_bootstrap_email", "ghost@example.com")
    await bootstrap_admin(db_session)
