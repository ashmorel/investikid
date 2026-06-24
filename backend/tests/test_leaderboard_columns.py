import pytest
from sqlalchemy import select

from app.models.user import User
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_user_has_leaderboard_columns(client, db_session):
    await _register_and_login(client, email="lb1@example.com", username="lb1")
    user = await db_session.scalar(select(User).where(User.email == "lb1@example.com"))
    assert user.display_handle is None          # not generated yet
    assert user.leaderboard_consent is False     # default off
    assert user.leaderboard_hidden is False       # default off
