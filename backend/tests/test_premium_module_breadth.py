import pytest

from app.seed.content import _MODULES

pytestmark = pytest.mark.asyncio(loop_scope="session")


def test_your_first_paycheque_is_premium_in_seed():
    spec = next(m for m in _MODULES if m["title"] == "Your First Paycheque")
    assert spec["is_premium"] is True


def test_premium_seed_count_is_three():
    assert sum(1 for m in _MODULES if m["is_premium"]) == 3


async def test_seed_refreshes_is_premium_on_existing_module(db_session):
    from sqlalchemy import select

    from app.models.content import Module
    from app.seed.content import seed_modules_and_lessons
    db_session.add(Module(topic="taxes", title="Your First Paycheque",
                          country_codes=[], is_premium=False, order_index=11, icon="💷"))
    await db_session.flush()
    await seed_modules_and_lessons(db_session)
    refreshed = await db_session.scalar(
        select(Module).where(Module.title == "Your First Paycheque")
    )
    assert refreshed.is_premium is True
