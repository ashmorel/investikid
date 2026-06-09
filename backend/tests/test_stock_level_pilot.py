from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.models.content import Lesson, Level, Module
from app.models.user import User, UserProgress
from app.seed.content import seed_modules_and_lessons

_asyncio = pytest.mark.asyncio(loop_scope="session")


async def _stock_levels(session):
    module = await session.scalar(
        select(Module).where(Module.topic == "stocks", Module.title == "What is a Stock?")
    )
    assert module is not None
    levels = (await session.scalars(
        select(Level).where(Level.module_id == module.id).order_by(Level.order_index)
    )).all()
    return module, levels


async def _lesson_count(session, level):
    return await session.scalar(
        select(func.count()).select_from(Lesson).where(Lesson.level_id == level.id)
    )


@_asyncio
async def test_stock_module_has_three_levels(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    _module, levels = await _stock_levels(db_session)
    assert [lv.order_index for lv in levels] == [0, 1, 2]
    assert [lv.is_premium for lv in levels] == [False, False, True]  # L1-2 free, L3 premium
    assert levels[1].title == "Level 2" and levels[2].title == "Level 3"

    # L2 = 2 cards + 4 quizzes + 1 scenario = 7; L3 = 2 cards + 4 quizzes + 1 scenario = 7
    assert await _lesson_count(db_session, levels[1]) == 7
    assert await _lesson_count(db_session, levels[2]) == 7


def test_stock_extra_levels_content_sane():
    from app.seed.content import _MODULES
    stock = next(m for m in _MODULES if m["topic"] == "stocks" and m["title"] == "What is a Stock?")
    for level in stock["extra_levels"]:
        assert level["title"] in {"Level 2", "Level 3"}
        for lsn in level["lessons"]:
            cj = lsn["content_json"]
            if lsn["type"] == "card":
                assert cj["title"] and cj["body"]
            elif lsn["type"] == "quiz":
                assert len(cj["choices"]) >= 2
                assert 0 <= cj["answer_index"] < len(cj["choices"])
                assert cj["question"] and cj["explanation"]
            elif lsn["type"] == "scenario":
                assert cj["prompt"]
                assert all(c["label"] and c["outcome"] for c in cj["choices"])
                assert 0 <= cj["correct_index"] < len(cj["choices"])
            else:
                raise AssertionError(f"unexpected lesson type {lsn['type']}")


@_asyncio
async def test_seed_is_idempotent(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    # Run again — re-seeding must not duplicate the stock module's levels/lessons.
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    _module, levels = await _stock_levels(db_session)
    assert [lv.order_index for lv in levels] == [0, 1, 2]
    l1_count = await _lesson_count(db_session, levels[0])
    assert await _lesson_count(db_session, levels[1]) == 7
    assert await _lesson_count(db_session, levels[2]) == 7
    # L1's count is unchanged after a second seed.
    assert await _lesson_count(db_session, levels[0]) == l1_count


async def _login_as(client, db_session, *, email, username, premium):
    user = User(
        email=email,
        username=username,
        password_hash=hash_password("SecurePass123!"),
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_premium=premium,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserProgress(user_id=user.id))
    await db_session.flush()

    r = await client.post(
        "/auth/login", json={"email": email, "password": "SecurePass123!"}
    )
    assert r.status_code == 200
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


@_asyncio
async def test_stock_level3_premium_gate_end_to_end(admin_client, db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    module, levels = await _stock_levels(db_session)
    stock_id = module.id
    level3 = next(lv for lv in levels if lv.order_index == 2 and lv.title == "Level 3")
    level3_id = str(level3.id)

    def _find(payload):
        return next(lv for lv in payload if str(lv["id"]) == level3_id)

    # Non-premium child: Level 3 is premium-locked.
    client = await _login_as(
        admin_client, db_session,
        email="stock_free_child@example.com", username="stockfreechild", premium=False,
    )
    r = await client.get(f"/modules/{stock_id}/levels")
    assert r.status_code == 200
    lv = _find(r.json())
    assert lv["is_premium"] is True
    assert lv["state"] == "locked"
    assert lv["locked_reason"] == "premium"

    # Premium child: same level is NOT premium-blocked (may be progression-locked).
    client = await _login_as(
        admin_client, db_session,
        email="stock_premium_child@example.com", username="stockpremiumchild", premium=True,
    )
    r = await client.get(f"/modules/{stock_id}/levels")
    assert r.status_code == 200
    lv = _find(r.json())
    assert lv["locked_reason"] != "premium"
