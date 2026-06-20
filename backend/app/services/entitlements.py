from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.subscription import Subscription
from app.models.user import User

# Statuses that grant entitlement across every provider.
ACTIVE_SUBSCRIPTION_STATUSES = frozenset(
    {"active", "trialing", "in_grace_period", "past_due"}
)


def household_key(user: User) -> str:
    """The billing household scope for a user: the parent email when present,
    else the user's own email (a self-managed teen is their own household).
    Lowercased to match household_token's normalization."""
    raw = user.parent_email or user.email or ""
    return raw.strip().lower()


def is_premium(user: User) -> bool:
    """Single read seam for premium entitlement.

    Today this is the per-child `is_premium` column. A future family or
    Stripe-backed model changes ONLY this function's internals — callers
    must never read `user.is_premium` directly.
    """
    return user.is_premium


def market_locked_for(user: User, market_code: str) -> bool:
    """A free user may progress in only their started market. Premium → never
    locked; free with no started market → nothing locked (first completion sets
    it); free with a started market → every OTHER market is locked."""
    if is_premium(user):
        return False
    if user.started_market_code is None:
        return False
    return market_code != user.started_market_code


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
    if value:
        # Local import: entitlements is imported by content paths, and the
        # analytics module must stay out of personalization import graphs.
        from app.services import product_analytics_service

        await product_analytics_service.record(
            session,
            "subscription_activated",
            user=child,
            role="child",
            props={"source": actor},
        )
    await session.flush()
    return True


def _row_entitles(row: Subscription, now: datetime) -> bool:
    """A subscription row entitles only if its status is active AND its period
    has not passed. A null period (providers that don't populate it) still
    entitles — the daily reconcile re-pulls those from the provider."""
    if row.status not in ACTIVE_SUBSCRIPTION_STATUSES:
        return False
    cpe = row.current_period_end
    if cpe is None:
        return True
    if cpe.tzinfo is None:
        cpe = cpe.replace(tzinfo=UTC)
    return cpe > now


async def recompute_household_premium(
    session: AsyncSession, parent_email: str
) -> None:
    """Recompute premium for every child of `parent_email` as the OR of all the
    household's subscription rows across providers. Idempotent; does not commit."""
    rows = (await session.scalars(
        select(Subscription).where(Subscription.parent_email == parent_email)
    )).all()
    now = datetime.now(UTC)
    entitled = any(_row_entitles(r, now) for r in rows)
    children = (await session.scalars(
        select(User).where(
            or_(
                User.parent_email == parent_email,
                and_(User.parent_email.is_(None), User.email == parent_email),
            )
        )
    )).all()
    for child in children:
        await set_premium(session, child, value=entitled, actor="billing:recompute")


def is_admin(user: User) -> bool:
    """Single read seam for admin entitlement.

    Today this is the per-user `is_admin` column. Callers must never read
    `user.is_admin` directly.
    """
    return user.is_admin


async def set_admin(
    session: AsyncSession, user: User, *, value: bool, actor: str
) -> bool:
    """Single write seam for admin entitlement.

    Idempotent: no-op (returns False, no audit row) when already at `value`.
    On change: flips the column and writes one AuditLog row attributing the
    change to `actor`. Does NOT commit — the caller owns the transaction
    (consistent with other service-layer writers).
    """
    old = user.is_admin
    if old == value:
        return False
    user.is_admin = value
    session.add(AuditLog(
        user_id=user.id,
        event_type="admin_grant" if value else "admin_revoke",
        metadata_json={"actor": actor, "old": old, "new": value},
    ))
    await session.flush()
    return True
