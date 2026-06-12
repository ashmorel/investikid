"""Parent-facing mastery report (M6).

Recomposes W3 mastery data into the paid product's evidence story: per child,
what was mastered in the window (objectives, standards), plus the digest's
weak-topic and next-recommendation enrichments. Window semantics differ from
the weekly digest (rolling N days vs since-last-digest), so this is its own
builder rather than a digest refactor.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Level, LevelMastery, Module
from app.models.user import User
from app.services.digest_service import _next_recommendation, _weak_topic

MAX_OBJECTIVES = 8


async def build_mastery_report(
    session: AsyncSession, parent_email: str, *, days: int = 30, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    since = now - timedelta(days=days)

    children = (
        await session.scalars(select(User).where(User.parent_email == parent_email))
    ).all()

    entries: list[dict[str, Any]] = []
    household_count = 0
    for child in children:
        rows = (
            await session.execute(
                select(LevelMastery, Level, Module)
                .join(Level, Level.id == LevelMastery.level_id)
                .join(Module, Module.id == Level.module_id)
                .where(
                    LevelMastery.user_id == child.id,
                    LevelMastery.mastered_at > since,
                    LevelMastery.mastered_at <= now,
                )
                .order_by(LevelMastery.mastered_at)
            )
        ).all()

        objectives: list[str] = []
        standards: list[dict] = []
        for _, level, module in rows:
            for obj in level.learning_objectives or []:
                if obj not in objectives:
                    objectives.append(obj)
            for std in module.standards_alignment or []:
                if std not in standards:
                    standards.append(std)

        mastered_total = (
            await session.scalar(
                select(func.count())
                .select_from(LevelMastery)
                .where(LevelMastery.user_id == child.id)
            )
        ) or 0

        recommendation, _module = await _next_recommendation(session, child)
        entries.append(
            {
                "user_id": str(child.id),
                "username": child.username,
                "mastered_count": len(rows),
                "mastered_total": mastered_total,
                "objectives": objectives[:MAX_OBJECTIVES],
                "standards": standards,
                "weak_topic": await _weak_topic(session, child),
                "next_recommendation": recommendation,
            }
        )
        household_count += len(rows)

    return {
        "window_days": days,
        "children": entries,
        "household_mastered_count": household_count,
    }
