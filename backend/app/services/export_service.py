from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail
from app.models.user import User, UserProgress


async def build_user_export(session: AsyncSession, user: User) -> dict[str, Any]:
    progress = await session.get(UserProgress, user.id)
    emails = (await session.scalars(
        select(SentEmail).where(
            (SentEmail.to_email == user.email)
            | (SentEmail.to_email == user.parent_email)
        )
    )).all()
    return {
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "dob": user.dob.isoformat(),
            "country_code": user.country_code,
            "currency_code": user.currency_code,
            "topic_path": user.topic_path,
            "parent_email": user.parent_email,
            "created_at": user.created_at.isoformat(),
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "policy_version_accepted": user.policy_version_accepted,
            "policy_accepted_at": user.policy_accepted_at.isoformat() if user.policy_accepted_at else None,
            "profiling_enabled": user.profiling_enabled,
            "marketing_opt_in": user.marketing_opt_in,
        },
        "progress": {
            "xp": progress.xp if progress else 0,
            "level": progress.level if progress else 1,
            "streak_count": progress.streak_count if progress else 0,
            "last_activity_date": (
                progress.last_activity_date.isoformat()
                if progress and progress.last_activity_date
                else None
            ),
        },
        "consent": {
            "parent_consent_given_at": (
                user.parent_consent_given_at.isoformat()
                if user.parent_consent_given_at
                else None
            ),
            "consent_declined_at": (
                user.consent_declined_at.isoformat()
                if user.consent_declined_at
                else None
            ),
        },
        "emails": [
            {"template": e.template, "to": e.to_email, "sent_at": e.sent_at.isoformat()} for e in emails
        ],
    }
