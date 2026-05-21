from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserProgress

_PASSWORD = "TestPassword1234!"


async def _ensure(session: AsyncSession, **kwargs) -> bool:
    existing = await session.scalar(
        select(User).where(User.username == kwargs["username"])
    )
    if existing:
        return False
    user = User(password_hash=hash_password(_PASSWORD), **kwargs)
    session.add(user)
    await session.flush()
    session.add(UserProgress(user_id=user.id))
    return True


async def seed_tier_accounts(session: AsyncSession) -> None:
    if settings.environment == "production":
        return
    now = datetime.now(UTC)
    await _ensure(
        session,
        email="tier-parent@test.invest-ed",
        username="tier_parent",
        dob=date(1990, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
        email_verified_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="premium-child@test.invest-ed",
        username="premium_child",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="tier-parent@test.invest-ed",
        is_active=True,
        is_premium=True,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="free-child@test.invest-ed",
        username="free_child",
        dob=date(2012, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="tier-parent@test.invest-ed",
        is_active=True,
        is_premium=False,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await session.commit()
