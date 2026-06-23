import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.arcade import ArcadeScore
from app.models.user import User, UserProgress

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_arcade_score_persists(db_session):
    user = User(
        username=f"arcadetest_{uuid.uuid4().hex[:8]}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(ArcadeScore(user_id=user.id, game="quiz_rush", points=120, market_code="GB"))
    await db_session.flush()
    row = (await db_session.scalars(select(ArcadeScore))).one()
    assert row.game == "quiz_rush" and row.points == 120 and row.market_code == "GB"


async def test_user_progress_has_arcade_cap_columns(db_session):
    cols = UserProgress.__table__.columns.keys()
    assert "arcade_xp_today" in cols and "arcade_xp_date" in cols
