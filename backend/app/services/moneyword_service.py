from collections import Counter
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markets import active_market
from app.models.arcade_word import ArcadeDailyPlay, ArcadeDailySchedule, ArcadeWord
from app.models.user import User, UserProgress
from app.services import arcade_service
from app.services.content_service import record_daily_activity

MAX_GUESSES = 6


def evaluate_guess(answer: str, guess: str) -> list[str]:
    answer, guess = answer.upper(), guess.upper()
    result = ["absent"] * len(guess)
    remaining = Counter(answer)
    # Pass 1: exact matches consume answer letters.
    for i, ch in enumerate(guess):
        if i < len(answer) and ch == answer[i]:
            result[i] = "correct"
            remaining[ch] -= 1
    # Pass 2: present only while an unconsumed copy remains.
    for i, ch in enumerate(guess):
        if result[i] == "correct":
            continue
        if remaining.get(ch, 0) > 0:
            result[i] = "present"
            remaining[ch] -= 1
    return result


class NoApprovedWords(Exception):
    """No approved MoneyWord words exist for the requested language."""


async def pick_daily_word(session: AsyncSession, *, language: str, today: date) -> ArcadeWord:
    existing = await session.scalar(
        select(ArcadeDailySchedule).where(
            ArcadeDailySchedule.puzzle_date == today, ArcadeDailySchedule.language == language
        )
    )
    if existing is not None:
        return await session.get(ArcadeWord, existing.word_id)

    # Least-recently-scheduled approved word: never-scheduled first (NULL last-scheduled),
    # then oldest most-recent schedule.
    last_sched = (
        select(ArcadeDailySchedule.word_id, func.max(ArcadeDailySchedule.puzzle_date).label("last"))
        .group_by(ArcadeDailySchedule.word_id)
        .subquery()
    )
    word = await session.scalar(
        select(ArcadeWord)
        .outerjoin(last_sched, last_sched.c.word_id == ArcadeWord.id)
        .where(ArcadeWord.status == "approved", ArcadeWord.language == language)
        .order_by(last_sched.c.last.asc().nulls_first(), ArcadeWord.created_at.asc())
        .limit(1)
    )
    if word is None:
        raise NoApprovedWords(language)
    session.add(ArcadeDailySchedule(puzzle_date=today, language=language, word_id=word.id))
    try:
        await session.flush()
    except IntegrityError:
        # Concurrent first-request created the row — re-read the winner.
        await session.rollback()
        existing = await session.scalar(
            select(ArcadeDailySchedule).where(
                ArcadeDailySchedule.puzzle_date == today, ArcadeDailySchedule.language == language
            )
        )
        return await session.get(ArcadeWord, existing.word_id)
    return word


class AlreadyCompleted(Exception):
    """The player has already finished today's MoneyWord puzzle."""


async def _load_play(session: AsyncSession, user: User, today: date, language: str) -> ArcadeDailyPlay:
    # Lock the row FOR UPDATE: two concurrent POSTs of the winning guess would
    # otherwise both read completed=False and both award coins/score. The lock
    # serialises them — the second waits, then sees completed=True and is rejected.
    def _locked():
        return (
            select(ArcadeDailyPlay)
            .where(ArcadeDailyPlay.user_id == user.id, ArcadeDailyPlay.puzzle_date == today)
            .with_for_update()
        )

    play = await session.scalar(_locked())
    if play is None:
        play = ArcadeDailyPlay(user_id=user.id, puzzle_date=today, language=language, guesses=[])
        session.add(play)
        try:
            await session.flush()
        except IntegrityError:
            # Concurrent first guess created the row — re-read it under the lock.
            await session.rollback()
            play = await session.scalar(_locked())
    return play


def _state(word: ArcadeWord, play: ArcadeDailyPlay) -> dict:
    return {
        "length": word.length,
        "max_guesses": MAX_GUESSES,
        "guesses": [{"word": g, "feedback": evaluate_guess(word.word, g)} for g in play.guesses],
        "completed": play.completed,
        "solved": play.solved,
        "definition": word.definition if play.completed else None,
        "already_played": play.completed,
    }


async def get_today(session: AsyncSession, user: User, *, today: date, language: str = "en") -> dict:
    word = await pick_daily_word(session, language=language, today=today)
    play = await session.scalar(
        select(ArcadeDailyPlay).where(
            ArcadeDailyPlay.user_id == user.id, ArcadeDailyPlay.puzzle_date == today
        )
    )
    if play is None:  # no row yet — empty board, don't create until first guess
        return {
            "length": word.length,
            "max_guesses": MAX_GUESSES,
            "guesses": [],
            "completed": False,
            "solved": False,
            "definition": None,
            "already_played": False,
        }
    return _state(word, play)


async def play_guess(
    session: AsyncSession, user: User, *, guess: str, today: date, language: str = "en"
) -> dict:
    word = await pick_daily_word(session, language=language, today=today)
    g = (guess or "").strip().upper()
    if len(g) != word.length or not g.isalpha():
        raise ValueError("guess must be the right length and letters only")
    play = await _load_play(session, user, today, language)
    if play.completed:
        raise AlreadyCompleted()
    play.guesses = [*play.guesses, g]
    solved = g == word.word
    out_of_guesses = len(play.guesses) >= MAX_GUESSES
    if solved or out_of_guesses:
        play.completed = True
        play.solved = solved
        if solved:
            points = max(1, MAX_GUESSES - len(play.guesses) + 1) * 10
            progress = await session.get(UserProgress, user.id)
            market = active_market(user)
            await arcade_service.award_arcade_coins(session, progress, 5, market_code=market)
            await arcade_service.record_score(
                session, user_id=user.id, game="moneyword", points=points, market_code=market
            )
            record_daily_activity(progress, today)
    await session.flush()
    return _state(word, play)
