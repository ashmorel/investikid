"""Limited-edition collectables: evaluate per-drop goals and auto-grant earned drops.
A drop is a CosmeticItem with unlock_type set; active iff now is within its window."""
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arcade import ArcadeScore
from app.models.content import Lesson, LessonCompletion
from app.models.cosmetics import CosmeticItem, UserCosmetic
from app.models.user import UserProgress

log = logging.getLogger(__name__)


def is_drop_active(item: CosmeticItem, now: datetime) -> bool:
    if item.unlock_type is None:
        return False
    if item.available_from is not None and now < item.available_from:
        return False
    if item.available_until is not None and now > item.available_until:
        return False
    return True


async def _streak_days(session, progress, item) -> int:
    return progress.streak_count


async def _window_xp(session, progress, item) -> int:
    stmt = (select(func.coalesce(func.sum(Lesson.xp_reward), 0))
            .join(LessonCompletion, LessonCompletion.lesson_id == Lesson.id)
            .where(LessonCompletion.user_id == progress.user_id,
                   LessonCompletion.completed_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


async def _window_lessons(session, progress, item) -> int:
    stmt = (select(func.count()).select_from(LessonCompletion)
            .where(LessonCompletion.user_id == progress.user_id,
                   LessonCompletion.completed_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


async def _window_arcade(session, progress, item) -> int:
    stmt = (select(func.coalesce(func.sum(ArcadeScore.points), 0))
            .where(ArcadeScore.user_id == progress.user_id,
                   ArcadeScore.created_at >= item.available_from))
    return int(await session.scalar(stmt) or 0)


_EVALUATORS: dict[str, Callable[[AsyncSession, UserProgress, CosmeticItem], Awaitable[int]]] = {
    "streak_days": _streak_days,
    "window_xp": _window_xp,
    "window_lessons": _window_lessons,
    "window_arcade": _window_arcade,
}


async def progress_for(session: AsyncSession, progress: UserProgress, item: CosmeticItem) -> int:
    ev = _EVALUATORS.get(item.unlock_type or "")
    if ev is None:
        return 0
    return await ev(session, progress, item)


async def grant_eligible(session: AsyncSession, progress: UserProgress) -> list[str]:
    """Grant any active, un-owned drop whose goal the user meets. Idempotent.
    Defensive: never raises into the caller's (XP) flow."""
    try:
        now = datetime.now(UTC)
        drops = (await session.scalars(select(CosmeticItem).where(CosmeticItem.unlock_type.isnot(None)))).all()
        active = [d for d in drops if is_drop_active(d, now) and d.unlock_type in _EVALUATORS]
        if not active:
            return []
        owned_ids = set((await session.scalars(
            select(UserCosmetic.item_id).where(UserCosmetic.user_id == progress.user_id))).all())
        granted: list[str] = []
        for d in active:
            if d.id in owned_ids:
                continue
            if await progress_for(session, progress, d) >= (d.unlock_threshold or 0):
                session.add(UserCosmetic(user_id=progress.user_id, item_id=d.id, equipped=False,
                                         unlocked_at=now))
                granted.append(d.slug)
        if granted:
            await session.flush()
        return granted
    except Exception:  # never break the learning flow
        log.exception("grant_eligible failed")
        return []
