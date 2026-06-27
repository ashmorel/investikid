from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.consent import SentEmail
from app.models.feedback import Feedback
from app.models.push_device import PushDevice
from app.models.user import User


async def purge_expired_accounts(session: AsyncSession, today: date) -> int:
    """Hard-overwrite PII for accounts soft-deleted past the retention window.

    Overwrites email, username, password_hash, parent_email, and topic_path with
    null / placeholder values for any account whose deleted_at is older than
    ``settings.data_retention_days`` before midnight on ``today`` (UTC).

    ``dob`` and ``country_code`` are intentionally retained: once the direct
    identifiers above are removed those fields are no longer considered
    identifying; they are kept for age-gate audit trails and aggregate analytics
    as documented in the DPIA.

    Soft-delete never fires the User FK CASCADEs, so child-linked PII in other
    tables would otherwise outlive the purge. Explicitly hard-delete it here:
      - ``sent_emails`` (raw recipient address + body) for this user's subject_id
      - ``push_devices`` (device tokens) for this user
      - ``feedback`` rows submitted by this user

    Idempotent: rows that already have ``purged_at`` set are skipped.
    Returns the number of rows purged.
    """
    cutoff = datetime.combine(today, time.min, tzinfo=UTC) - timedelta(
        days=settings.data_retention_days
    )
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
    if rows:
        purged_ids = [u.id for u in rows]
        # Hard-delete child-linked PII that soft-delete left behind.
        await session.execute(delete(SentEmail).where(SentEmail.subject_id.in_(purged_ids)))
        await session.execute(delete(PushDevice).where(PushDevice.user_id.in_(purged_ids)))
        await session.execute(delete(Feedback).where(Feedback.user_id.in_(purged_ids)))
        # Sever the pseudonymous analytics join key at the same moment the
        # direct identifiers go (events stay as anonymous counts).
        from app.services import product_analytics_service

        await product_analytics_service.detach_user(session, purged_ids)
    await session.commit()
    return len(rows)
