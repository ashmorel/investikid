import pytest

from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_guardian_attested_at_defaults_none_and_persists(db_session):
    from datetime import UTC, date, datetime

    user = User(
        username="kid_attest",
        password_hash="x",
        dob=date(2015, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@example.com",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    assert user.guardian_attested_at is None

    now = datetime.now(UTC)
    user.guardian_attested_at = now
    await db_session.flush()
    fetched = await db_session.get(User, user.id)
    assert fetched.guardian_attested_at is not None
