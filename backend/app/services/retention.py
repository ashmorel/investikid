from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User


async def purge_expired_accounts(session: AsyncSession, today: date) -> int:
    """Hard-overwrite PII for accounts soft-deleted past the retention window.

    Idempotent: rows already purged (purged_at set) are skipped.
    Returns the number of rows purged.
    """
    cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_days)
    rows = (await session.scalars(
        select(User)
        .where(
            User.deleted_at.is_not(None),
            User.deleted_at < cutoff,
            User.purged_at.is_(None),
        )
        .execution_options(include_deleted=True)
    )).all()
    now = datetime.now(UTC)
    for u in rows:
        u.email = None
        u.username = f"purged_{u.id}"
        u.password_hash = ""
        u.parent_email = None
        u.topic_path = None
        u.purged_at = now
    await session.commit()
    return len(rows)
