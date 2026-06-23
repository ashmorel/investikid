from collections import Counter
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade_word import ArcadeDailySchedule, ArcadeWord

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
