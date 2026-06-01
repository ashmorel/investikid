"""Deploy-time admin bootstrap (idempotent).

If ADMIN_BOOTSTRAP_EMAIL is set, grant is_admin to the matching user on each
deploy. Missing user is a no-op + warning (never raises) so it can't break
the seed/start sequence. Replaces needing a shell to run grant-admin.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.services.entitlements import set_admin

logger = logging.getLogger(__name__)


async def bootstrap_admin(session: AsyncSession) -> None:
    email = settings.admin_bootstrap_email.strip()
    if not email:
        return
    user = await session.scalar(
        select(User).where(func.lower(User.email) == email.lower())
    )
    if user is None:
        logger.warning(
            "ADMIN_BOOTSTRAP_EMAIL=%s is set but no user has that email yet; "
            "skipping (will apply on a later deploy once that account exists).",
            email,
        )
        return
    changed = await set_admin(session, user, value=True, actor="bootstrap")
    logger.info("Admin bootstrap: %s is_admin granted (changed=%s)", user.username, changed)
