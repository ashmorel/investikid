from datetime import UTC, date, datetime, timedelta

import pytest

from app.models.user import User
from app.services.retention import purge_expired_accounts

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_purge_overwrites_pii_after_retention(db_session):
    old = datetime.now(UTC) - timedelta(days=40)
    u = User(
        email="purge@example.com", username="purgeme", password_hash="hash",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
        parent_email="pp@example.com", topic_path="core",
        is_active=False, deleted_at=old, deletion_requested_at=old,
    )
    db_session.add(u)
    await db_session.flush()

    n = await purge_expired_accounts(db_session, date.today())
    assert n == 1
    await db_session.refresh(u)
    assert u.purged_at is not None
    assert u.email is None
    assert u.parent_email is None
    assert u.topic_path is None
    assert u.username.startswith("purged_")
    assert u.password_hash == ""

    n2 = await purge_expired_accounts(db_session, date.today())
    assert n2 == 0


async def test_purge_skips_recent_deletions(db_session):
    recent = datetime.now(UTC) - timedelta(days=5)
    u = User(
        email="keep@example.com", username="keepme", password_hash="hash",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
        is_active=False, deleted_at=recent,
    )
    db_session.add(u)
    await db_session.flush()
    n = await purge_expired_accounts(db_session, date.today())
    assert n == 0
    await db_session.refresh(u)
    assert u.email == "keep@example.com"


async def test_cli_purge_command_runs(db_session, monkeypatch):
    import app.cli as cli

    async def fake_session_ctx():
        yield db_session

    monkeypatch.setattr(cli, "_session_scope", fake_session_ctx)
    code = await cli.run(["purge-accounts"])
    assert code == 0
