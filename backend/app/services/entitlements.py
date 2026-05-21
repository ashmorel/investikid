from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.user import User


def is_premium(user: User) -> bool:
    """Single read seam for premium entitlement.

    Today this is the per-child `is_premium` column. A future family or
    Stripe-backed model changes ONLY this function's internals — callers
    must never read `user.is_premium` directly.
    """
    return user.is_premium


async def set_premium(
    session: AsyncSession, child: User, *, value: bool, actor: str
) -> bool:
    """Single write seam for premium entitlement.

    Idempotent: no-op (returns False, no audit row) when already at `value`.
    On change: flips the column and writes one AuditLog row attributing the
    change to `actor`. Does NOT commit — the caller owns the transaction
    (consistent with other service-layer writers).
    """
    old = child.is_premium
    if old == value:
        return False
    child.is_premium = value
    session.add(AuditLog(
        user_id=child.id,
        event_type="premium_grant" if value else "premium_revoke",
        metadata_json={"actor": actor, "old": old, "new": value},
    ))
    await session.flush()
    return True
