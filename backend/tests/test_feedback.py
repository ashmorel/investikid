from datetime import date

import pytest

from app.models.feedback import Feedback
from app.models.user import User
from app.services.feedback_service import create_feedback

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _make_user(db_session, *, email: str) -> User:
    """Create and flush a minimal User row for FK compliance."""
    user = User(
        email=email,
        username=email.split("@")[0],
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_feedback_child(db_session):
    user = await _make_user(db_session, email="fb_child@example.com")

    fb = await create_feedback(
        db_session,
        feedback_type="bug",
        message="quiz timer broken",
        page_url="/lessons/1",
        user_id=user.id,
        parent_email=None,
        submitter_role="child",
    )
    assert fb.id is not None
    assert fb.submitter_role == "child"
    assert fb.feedback_type == "bug"
    assert fb.parent_email is None


async def test_create_feedback_parent(db_session):
    fb = await create_feedback(
        db_session,
        feedback_type="feature",
        message="please add dark mode",
        page_url=None,
        user_id=None,
        parent_email="mum@example.com",
        submitter_role="parent",
    )
    assert fb.parent_email == "mum@example.com"
    assert fb.user_id is None
    assert fb.submitter_role == "parent"
