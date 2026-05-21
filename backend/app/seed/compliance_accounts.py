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


async def seed_compliance_accounts(session: AsyncSession) -> None:
    if settings.environment == "production":
        return
    now = datetime.now(UTC)
    await _ensure(
        session,
        email=None,
        username="pending_consent_kid",
        dob=date(2016, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@test.invest-ed",
        is_active=False,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email=None,
        username="consented_kid",
        dob=date(2016, 1, 1),
        country_code="GB",
        currency_code="GBP",
        parent_email="parent@test.invest-ed",
        is_active=True,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="selfteen@test.invest-ed",
        username="selfteen",
        dob=date(2009, 1, 1),
        country_code="GB",
        currency_code="GBP",
        is_active=True,
        email_verified_at=None,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await session.commit()
