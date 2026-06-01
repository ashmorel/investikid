"""Deploy-time admin bootstrap (idempotent).

If ADMIN_BOOTSTRAP_EMAIL is set, grant is_admin to the matching user on each
deploy. The value matches the account's email OR username (case-insensitive),
so it works whether lee_ashmore@... is the learner's own email, their login
username, or neither-but-username. Missing user is a no-op + warning (never
raises) so it can't break the seed/start sequence. Avoids needing a shell to
run grant-admin. NB: deliberately does NOT match parent_email — that can be
shared across sibling accounts and must never grant admin broadly.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.services.entitlements import set_admin

logger = logging.getLogger(__name__)


async def bootstrap_admin(session: AsyncSession) -> None:
    ident = settings.admin_bootstrap_email.strip()
    if not ident:
        return
    needle = ident.lower()
    user = await session.scalar(
        select(User).where(
            (func.lower(User.email) == needle) | (func.lower(User.username) == needle)
        )
    )
    if user is None:
        logger.warning(
            "ADMIN_BOOTSTRAP_EMAIL=%s is set but no user matches that email or "
            "username yet; skipping (will apply on a later deploy once it exists).",
            ident,
        )
        return
    changed = await set_admin(session, user, value=True, actor="bootstrap")
    logger.info("Admin bootstrap: %s is_admin granted (changed=%s)", user.username, changed)
