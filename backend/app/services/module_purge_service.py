from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.content import Lesson, Module


async def purge_archived_modules(session: AsyncSession, *, now: datetime) -> int:
    """Hard-delete modules archived longer than the retention window. DB-level
    ON DELETE CASCADE removes levels/lessons/progress; lessons are deleted
    explicitly first to match the original delete_module path. Returns the count."""
    cutoff = now - timedelta(days=settings.archived_module_retention_days)
    ids = (await session.execute(
        select(Module.id).where(Module.archived_at.is_not(None),
                                Module.archived_at < cutoff)
    )).scalars().all()
    if not ids:
        return 0
    await session.execute(delete(Lesson).where(Lesson.module_id.in_(ids)))
    await session.execute(delete(Module).where(Module.id.in_(ids)))
    return len(ids)
