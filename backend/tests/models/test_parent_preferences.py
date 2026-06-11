import pytest

from app.models.parent_preferences import ParentPreferences

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_parent_preferences_defaults_opt_out_false(db_session):
    pref = ParentPreferences(parent_email="p@example.com")
    db_session.add(pref)
    await db_session.flush()

    fetched = await db_session.get(ParentPreferences, "p@example.com")
    assert fetched is not None
    assert fetched.trial_reminder_opt_out is False
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


async def test_parent_preferences_weekly_digest_defaults(db_session):
    pref = ParentPreferences(parent_email="digest@example.com")
    db_session.add(pref)
    await db_session.flush()

    fetched = await db_session.get(ParentPreferences, "digest@example.com")
    assert fetched is not None
    assert fetched.weekly_digest_opt_out is False
    assert fetched.last_digest_sent_at is None
