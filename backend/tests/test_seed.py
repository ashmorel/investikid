import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Module
from app.seed.content import seed_modules_and_lessons

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_seed_creates_starter_content(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()

    module_count = await db_session.scalar(select(func.count()).select_from(Module))
    lesson_count = await db_session.scalar(select(func.count()).select_from(Lesson))
    assert module_count >= 12
    assert lesson_count >= 49


async def test_seed_is_idempotent(db_session):
    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    first = await db_session.scalar(select(func.count()).select_from(Module))

    await seed_modules_and_lessons(db_session)
    await db_session.commit()
    second = await db_session.scalar(select(func.count()).select_from(Module))

    assert first == second


async def test_compliance_accounts_seed_idempotent(db_session):
    from app.models.user import User
    from app.seed.compliance_accounts import seed_compliance_accounts

    await seed_compliance_accounts(db_session)
    await seed_compliance_accounts(db_session)
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_(["pending_consent_kid", "consented_kid", "selfteen"])
        )
    )
    assert count == 3


async def test_tier_accounts_seed_idempotent(db_session):
    from sqlalchemy import func, select

    from app.models.user import User
    from app.seed.tier_accounts import seed_tier_accounts

    await seed_tier_accounts(db_session)
    await seed_tier_accounts(db_session)
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_(["tier_parent", "premium_child", "free_child"])
        )
    )
    assert count == 3
    premium = await db_session.scalar(
        select(User).where(User.username == "premium_child"))
    free = await db_session.scalar(
        select(User).where(User.username == "free_child"))
    assert premium.is_premium is True
    assert free.is_premium is False
    assert premium.parent_email == "tier-parent@test.invest-ed"
    assert free.parent_email == "tier-parent@test.invest-ed"


async def test_tier_accounts_seed_prod_guarded(db_session, monkeypatch):
    from sqlalchemy import func, select

    from app.core.config import settings
    from app.models.user import User
    from app.seed.tier_accounts import seed_tier_accounts

    monkeypatch.setattr(settings, "environment", "production")
    await seed_tier_accounts(db_session)
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_(["tier_parent", "premium_child", "free_child"])
        )
    )
    assert count == 0
