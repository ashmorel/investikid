from datetime import date

import pytest
from sqlalchemy import select

from app import cli
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _mk(session, username, email):
    u = User(
        email=email, username=username, password_hash="x",
        dob=date(2012, 1, 1), country_code="GB", currency_code="GBP",
        is_premium=False,
    )
    session.add(u)
    await session.flush()
    return u


async def test_grant_premium_by_username_then_revoke(db_session, monkeypatch):
    u = await _mk(db_session, "cliuser1", "cliuser1@example.com")
    uid = u.id

    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)

    code = await cli.run(["grant-premium", "cliuser1"])
    assert code == 0
    refreshed = await db_session.scalar(select(User).where(User.id == uid))
    assert refreshed.is_premium is True

    code = await cli.run(["grant-premium", "cliuser1", "--revoke"])
    assert code == 0
    refreshed = await db_session.scalar(select(User).where(User.id == uid))
    assert refreshed.is_premium is False


async def test_grant_premium_by_email(db_session, monkeypatch):
    await _mk(db_session, "cliuser2", "cliuser2@example.com")

    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)

    code = await cli.run(["grant-premium", "cliuser2@example.com"])
    assert code == 0
    u = await db_session.scalar(select(User).where(User.username == "cliuser2"))
    assert u.is_premium is True


async def test_grant_premium_unknown_user_exit_2(db_session, monkeypatch):
    async def fake_scope():
        yield db_session
    monkeypatch.setattr(cli, "_session_scope", fake_scope)
    code = await cli.run(["grant-premium", "nobody@example.com"])
    assert code == 2
