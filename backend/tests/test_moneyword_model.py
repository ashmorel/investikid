import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.arcade_word import ArcadeDailyPlay, ArcadeDailySchedule, ArcadeWord
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_word_persists(db_session):
    db_session.add(
        ArcadeWord(
            word="ASSET",
            definition="Something valuable you own.",
            language="en",
            length=5,
            status="approved",
            source="manual",
        )
    )
    await db_session.flush()
    row = (await db_session.scalars(select(ArcadeWord).where(ArcadeWord.word == "ASSET"))).first()
    assert row.word == "ASSET" and row.status == "approved" and row.length == 5


async def test_word_unique_constraint_exists(db_session):
    cols = ArcadeWord.__table__.constraints
    names = {c.name for c in cols}
    assert "uq_arcade_word_lang" in names


async def test_daily_schedule_persists(db_session):
    word = ArcadeWord(
        word="STOCK",
        definition="A share of ownership in a company.",
        language="en",
        length=5,
        status="approved",
        source="manual",
    )
    db_session.add(word)
    await db_session.flush()

    db_session.add(
        ArcadeDailySchedule(
            puzzle_date=date(2026, 7, 1),
            language="en",
            word_id=word.id,
        )
    )
    await db_session.flush()
    row = (
        await db_session.scalars(
            select(ArcadeDailySchedule).where(ArcadeDailySchedule.puzzle_date == date(2026, 7, 1))
        )
    ).first()
    assert row.language == "en" and row.word_id == word.id


async def test_daily_schedule_unique_constraint_exists(db_session):
    names = {c.name for c in ArcadeDailySchedule.__table__.constraints}
    assert "uq_arcade_daily_date_lang" in names


async def test_daily_play_persists(db_session):
    user = User(
        username=f"mwtest_{uuid.uuid4().hex[:8]}",
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        ArcadeDailyPlay(
            user_id=user.id,
            puzzle_date=date(2026, 7, 1),
            language="en",
            guesses=["MONEY", "STOCK"],
            solved=True,
            completed=True,
        )
    )
    await db_session.flush()
    row = (
        await db_session.scalars(
            select(ArcadeDailyPlay).where(ArcadeDailyPlay.user_id == user.id)
        )
    ).first()
    assert row.solved is True and row.guesses == ["MONEY", "STOCK"]


async def test_daily_play_unique_constraint_exists(db_session):
    names = {c.name for c in ArcadeDailyPlay.__table__.constraints}
    assert "uq_arcade_daily_play_user_date" in names


async def test_arcade_word_table_columns(db_session):
    cols = ArcadeWord.__table__.columns.keys()
    for col in ("id", "word", "definition", "language", "length", "status", "source", "created_at"):
        assert col in cols, f"Missing column: {col}"


async def test_arcade_daily_play_table_columns(db_session):
    cols = ArcadeDailyPlay.__table__.columns.keys()
    for col in ("id", "user_id", "puzzle_date", "language", "guesses", "solved", "completed", "created_at", "updated_at"):
        assert col in cols, f"Missing column: {col}"
