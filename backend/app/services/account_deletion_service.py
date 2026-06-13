"""Parent self-account deletion (Apple Guideline 5.1.1(v) compliance).

A "parent account" has no User row of its own — it is the constellation of
rows keyed by ``parent_email``. Deletion is DESTRUCTIVE and irreversible:

- Children (``User``) are *soft-deleted* (mirroring ``parent.py:erase_child``)
  so downstream FK references and audit history stay intact.
- Everything that lets a parent re-authenticate or that holds parent-side
  state is *hard-deleted*: sessions, OAuth identities, preferences,
  subscriptions, premium requests, feedback, and parent-owned groups.

Billing held in App Store / Play / Stripe is external to this database and is
NOT cancelled here — the UI must warn the parent to cancel it separately.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.consent import OneTimeToken
from app.models.feedback import Feedback
from app.models.group import LeaderboardGroup
from app.models.parent_identity import ParentIdentity
from app.models.parent_preferences import ParentPreferences
from app.models.parent_session import ParentSession
from app.models.premium_request import PremiumRequest
from app.models.subscription import Subscription
from app.models.user import User


async def delete_parent_account(session: AsyncSession, parent_email: str) -> dict:
    """Delete every trace of a parent account, in one transaction.

    Idempotent-ish: if nothing exists for ``parent_email`` it still returns ok.
    """
    now = datetime.now(UTC)

    # 1. Soft-delete this parent's children (reuse erase_child semantics).
    children = (await session.scalars(
        select(User)
        .where(User.parent_email == parent_email)
        .execution_options(include_deleted=True)
    )).all()
    from app.services import biometric_service
    children_deleted = 0
    for child in children:
        if child.deleted_at is not None:
            continue
        child.deletion_requested_at = now
        child.deleted_at = now
        child.is_active = False
        children_deleted += 1
        await biometric_service.revoke_subject(session, subject_key=biometric_service.subject_key_for_child(child.id))

    await biometric_service.revoke_subject(session, subject_key=biometric_service.subject_key_for_parent(parent_email))

    # 2. Hard-delete parent-owned groups. GroupMembership.group_id carries an
    #    ondelete="CASCADE" FK, so deleting the group removes its memberships
    #    (including members from other families) — that is correct: the group
    #    no longer exists. Other parents' groups are never selected here.
    await session.execute(
        delete(LeaderboardGroup).where(LeaderboardGroup.owner_parent_email == parent_email)
    )

    # 3. Hard-delete everything else keyed by parent_email.
    await session.execute(
        delete(ParentSession).where(ParentSession.parent_email == parent_email)
    )
    await session.execute(
        delete(ParentIdentity).where(ParentIdentity.parent_email == parent_email)
    )
    await session.execute(
        delete(ParentPreferences).where(ParentPreferences.parent_email == parent_email)
    )
    await session.execute(
        delete(PremiumRequest).where(PremiumRequest.parent_email == parent_email)
    )
    await session.execute(
        delete(Subscription).where(Subscription.parent_email == parent_email)
    )
    await session.execute(
        delete(Feedback).where(Feedback.parent_email == parent_email)
    )
    # Purge any outstanding magic-link tokens so a link issued shortly before
    # deletion can't re-authenticate into the now-deleted account.
    await session.execute(
        delete(OneTimeToken).where(OneTimeToken.email == parent_email)
    )

    # 4. Audit (content-free beyond the count, mirroring existing audit rows).
    session.add(AuditLog(
        event_type="parent_account_deleted",
        metadata_json={"children_deleted": children_deleted},
    ))

    await session.commit()
    return {"status": "ok", "children_deleted": children_deleted}
