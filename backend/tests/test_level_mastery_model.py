import datetime as dt
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.content import Level, LevelMastery, Module
from app.models.user import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _user() -> User:
    return User(
        username=f"c{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@x.test",
        password_hash="x",
        dob=dt.date(2015, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="p@x.test",
    )


async def _module_and_level(db_session) -> tuple[Module, Level]:
    m = Module(
        topic="savings",
        title="LM Mod",
        country_codes=[],
        is_premium=False,
        order_index=0,
        icon="📈",
    )
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    return m, lv


async def test_level_mastery_roundtrips(db_session):
    _, lv = await _module_and_level(db_session)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    mastered_at = datetime.now(UTC)
    db_session.add(
        LevelMastery(user_id=user.id, level_id=lv.id, mastered_at=mastered_at, score=0.85)
    )
    await db_session.flush()

    got = await db_session.scalar(
        select(LevelMastery).where(
            LevelMastery.user_id == user.id, LevelMastery.level_id == lv.id
        )
    )
    assert got is not None
    assert got.score == 0.85
    assert got.mastered_at == mastered_at


async def test_level_mastery_duplicate_user_level_rejected(db_session):
    _, lv = await _module_and_level(db_session)
    user = _user()
    db_session.add(user)
    await db_session.flush()

    db_session.add(
        LevelMastery(user_id=user.id, level_id=lv.id, mastered_at=datetime.now(UTC), score=0.9)
    )
    await db_session.flush()

    db_session.add(
        LevelMastery(user_id=user.id, level_id=lv.id, mastered_at=datetime.now(UTC), score=0.95)
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_module_and_level_json_fields_roundtrip(db_session):
    m, lv = await _module_and_level(db_session)
    m.standards_alignment = [{"framework": "Jump$tart", "code": "FD-1"}]
    m.sources = [{"title": "Bank of England", "url": "https://example.test"}]
    lv.learning_objectives = ["Explain saving vs spending"]
    await db_session.flush()
    await db_session.refresh(m)
    await db_session.refresh(lv)

    got_m = await db_session.scalar(select(Module).where(Module.id == m.id))
    got_lv = await db_session.scalar(select(Level).where(Level.id == lv.id))
    assert got_m.standards_alignment == [{"framework": "Jump$tart", "code": "FD-1"}]
    assert got_m.sources == [{"title": "Bank of England", "url": "https://example.test"}]
    assert got_lv.learning_objectives == ["Explain saving vs spending"]


async def test_new_json_fields_default_to_none(db_session):
    m, lv = await _module_and_level(db_session)
    assert m.standards_alignment is None
    assert m.sources is None
    assert lv.learning_objectives is None
