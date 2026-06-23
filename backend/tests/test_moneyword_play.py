"""Tests for moneyword_service play loop (Task 4)."""
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.arcade import ArcadeScore
from app.models.arcade_word import ArcadeWord
from app.models.user import User, UserProgress
from app.services.moneyword_service import AlreadyCompleted, get_today, play_guess

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2030, 7, 1)
LANGUAGE = "en"


async def _seed_word(db_session, word="ASSET") -> ArcadeWord:
    w = ArcadeWord(
        word=word,
        definition="A resource with economic value.",
        language=LANGUAGE,
        length=len(word),
        status="approved",
        source="manual",
    )
    db_session.add(w)
    await db_session.flush()
    return w


async def _user(db_session):
    username = f"mw_{uuid.uuid4().hex[:8]}"
    u = User(
        username=username,
        password_hash="x",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        active_market_code="GB",
    )
    db_session.add(u)
    await db_session.flush()
    p = UserProgress(user_id=u.id)
    db_session.add(p)
    await db_session.flush()
    return u, p


async def test_get_today_before_any_guess_returns_empty_board(db_session):
    await _seed_word(db_session)
    u, _p = await _user(db_session)
    state = await get_today(db_session, u, today=TODAY, language=LANGUAGE)
    assert state["completed"] is False
    assert state["solved"] is False
    assert state["guesses"] == []
    assert state["definition"] is None
    assert state["already_played"] is False


async def test_correct_first_guess_solves_puzzle(db_session):
    await _seed_word(db_session)
    u, p = await _user(db_session)
    state = await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)
    assert state["completed"] is True
    assert state["solved"] is True
    assert state["definition"] is not None  # revealed on completion
    assert len(state["guesses"]) == 1
    assert state["guesses"][0]["word"] == "ASSET"


async def test_correct_guess_awards_points(db_session):
    await _seed_word(db_session)
    u, p = await _user(db_session)
    await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)
    # An arcade_scores row should exist for this user with game="moneyword".
    row = await db_session.scalar(
        select(ArcadeScore).where(ArcadeScore.user_id == u.id, ArcadeScore.game == "moneyword")
    )
    assert row is not None
    assert row.points > 0


async def test_correct_guess_advances_streak(db_session):
    await _seed_word(db_session)
    u, p = await _user(db_session)
    streak_before = p.streak_count
    await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)
    assert p.streak_count == streak_before + 1


async def test_second_play_same_day_raises_already_completed(db_session):
    await _seed_word(db_session)
    u, _p = await _user(db_session)
    await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)
    with pytest.raises(AlreadyCompleted):
        await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)


async def test_wrong_length_guess_raises_value_error(db_session):
    await _seed_word(db_session)
    u, _p = await _user(db_session)
    with pytest.raises(ValueError):
        await play_guess(db_session, u, guess="CASH", today=TODAY, language=LANGUAGE)  # 4 letters, word is 5


async def test_get_today_after_play_returns_state(db_session):
    await _seed_word(db_session)
    u, _p = await _user(db_session)
    await play_guess(db_session, u, guess="ASSET", today=TODAY, language=LANGUAGE)
    state = await get_today(db_session, u, today=TODAY, language=LANGUAGE)
    assert state["completed"] is True
    assert state["already_played"] is True
    assert state["definition"] is not None
