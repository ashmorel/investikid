import datetime as dt

import pytest

from app.models.arcade_word import ArcadeWord
from app.services.moneyword_service import NoApprovedWords, pick_daily_word

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_words(db_session, *words):
    for w in words:
        db_session.add(
            ArcadeWord(
                word=w,
                definition=f"def {w}",
                language="en",
                length=len(w),
                status="approved",
                source="manual",
            )
        )
    await db_session.flush()


async def test_no_words_raises(db_session):
    with pytest.raises(NoApprovedWords):
        await pick_daily_word(db_session, language="en", today=dt.date(2026, 7, 1))


async def test_lazy_idempotent_and_no_repeat(db_session):
    await _seed_words(db_session, "ASSET", "BUDGET")
    d1 = dt.date(2026, 7, 2)
    d2 = dt.date(2026, 7, 3)
    w1 = await pick_daily_word(db_session, language="en", today=d1)
    w1b = await pick_daily_word(db_session, language="en", today=d1)
    assert w1.id == w1b.id  # idempotent same-day
    w2 = await pick_daily_word(db_session, language="en", today=d2)
    assert w2.id != w1.id  # no-repeat next day
