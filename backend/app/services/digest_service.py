"""Weekly parent digest — builder + runner (W4).

Builds a per-parent summary of the household's last week of learning and
sends it via the `weekly_digest` email template. The email template itself
is rendered by the email service (Task 3); this module owns the context.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import LessonCompletion, Level, LevelMastery, Module
from app.models.parent_preferences import ParentPreferences
from app.models.subscription import Subscription
from app.models.user import User, UserProgress
from app.services import product_analytics_service
from app.services.email import get_email_sender, premium_variant
from app.services.entitlements import ACTIVE_SUBSCRIPTION_STATUSES
from app.services.gap_detection_service import get_strengths_and_gaps
from app.services.recommendation_service import get_recommendations

logger = logging.getLogger(__name__)

DIGEST_INTERVAL = timedelta(days=7)


async def _is_parent_subscribed(session: AsyncSession, parent_email: str) -> bool:
    """Mirror of the entitlement predicate used by billing recompute."""
    statuses = (await session.scalars(
        select(Subscription.status).where(Subscription.parent_email == parent_email)
    )).all()
    return any(s in ACTIVE_SUBSCRIPTION_STATUSES for s in statuses)


async def _weak_topic(session: AsyncSession, child: User) -> str | None:
    """Weakest topic for a child — never fails the digest on an enrichment."""
    try:
        result = await get_strengths_and_gaps(session, child.id)
        for topic in result.topics:  # sorted: needs_practice first
            if topic.status == "needs_practice":
                return topic.topic
    except Exception:  # noqa: BLE001 — enrichment only
        logger.warning("digest: strengths/gaps failed for child %s", child.id, exc_info=True)
    return None


async def _next_recommendation(
    session: AsyncSession, child: User
) -> tuple[dict[str, Any] | None, Module | None]:
    """Top recommendation for a child — never fails the digest on an enrichment."""
    try:
        recs = await get_recommendations(session, child)
        for category in ("continue_learning", "practise_again", "something_new"):
            items = recs.get(category) or []
            if items:
                item = items[0]
                module = await session.get(Module, item["module_id"])
                if module is None:
                    return None, None
                return {
                    "module_title": module.title,
                    "level_title": item.get("level_title"),
                    "reason": item.get("reason"),
                }, module
    except Exception:  # noqa: BLE001 — enrichment only
        logger.warning("digest: recommendations failed for child %s", child.id, exc_info=True)
    return None, None


async def build_weekly_digest(
    session: AsyncSession, parent_email: str, *, now: datetime | None = None
) -> dict | None:
    """Build the weekly digest context for one parent, or None for a quiet week.

    Window = (max(last_digest_sent_at, now - 7d), now]. A digest is worth
    sending only if at least one child mastered a level or completed a
    lesson inside the window.
    """
    now = now or datetime.now(UTC)

    children = (await session.scalars(
        select(User).where(User.parent_email == parent_email)
    )).all()
    if not children:
        return None

    prefs = await session.get(ParentPreferences, parent_email)
    window_start = now - DIGEST_INTERVAL
    if prefs is not None and prefs.last_digest_sent_at is not None:
        window_start = max(window_start, prefs.last_digest_sent_at)

    child_entries: list[dict[str, Any]] = []
    has_activity = False

    for child in children:
        mastery_rows = (await session.execute(
            select(LevelMastery, Level, Module)
            .join(Level, Level.id == LevelMastery.level_id)
            .join(Module, Module.id == Level.module_id)
            .where(
                LevelMastery.user_id == child.id,
                LevelMastery.mastered_at > window_start,
                LevelMastery.mastered_at <= now,
            )
            .order_by(LevelMastery.mastered_at)
        )).all()

        masteries = [
            {
                "module_title": module.title,
                "level_title": level.title,
                "objectives": level.learning_objectives,
            }
            for _, level, module in mastery_rows
        ]

        lessons_completed = await session.scalar(
            select(func.count(LessonCompletion.id)).where(
                LessonCompletion.user_id == child.id,
                LessonCompletion.completed_at > window_start,
                LessonCompletion.completed_at <= now,
            )
        ) or 0

        if masteries or lessons_completed:
            has_activity = True

        progress = await session.get(UserProgress, child.id)
        streak = progress.streak_count if progress is not None else 0

        weak_topic = await _weak_topic(session, child)
        recommendation, rec_module = await _next_recommendation(session, child)

        # Conversation prompt: most recently mastered module in window with
        # a prompt, else the recommended module's prompt, else None.
        conversation_prompt = None
        for _, _, module in reversed(mastery_rows):
            if module.conversation_prompt:
                conversation_prompt = module.conversation_prompt
                break
        if conversation_prompt is None and rec_module is not None:
            conversation_prompt = rec_module.conversation_prompt

        child_entries.append({
            "name": child.username,
            "masteries": masteries,
            "lessons_completed": lessons_completed,
            "streak": streak,
            "weak_topic": weak_topic,
            "next_recommendation": recommendation,
            "conversation_prompt": conversation_prompt,
        })

    if not has_activity:
        return None

    return {
        "parent_email": parent_email,
        "week_start": window_start.isoformat(),
        "week_end": now.isoformat(),
        "children": child_entries,
        "parent_subscribed": await _is_parent_subscribed(session, parent_email),
    }


async def run_weekly_digests(
    session: AsyncSession, *, now: datetime | None = None
) -> dict:
    """Send weekly digests to every eligible parent. Commits on completion."""
    now = now or datetime.now(UTC)

    parent_emails = (await session.scalars(
        select(User.parent_email).where(User.parent_email.is_not(None)).distinct()
    )).all()

    sender = get_email_sender()
    summary = {"sent": 0, "skipped_quiet": 0, "skipped_recent": 0, "skipped_opt_out": 0}

    for parent_email in parent_emails:
        prefs = await session.get(ParentPreferences, parent_email)
        if prefs is not None and prefs.weekly_digest_opt_out:
            summary["skipped_opt_out"] += 1
            continue
        if (
            prefs is not None
            and prefs.last_digest_sent_at is not None
            and prefs.last_digest_sent_at > now - DIGEST_INTERVAL
        ):
            summary["skipped_recent"] += 1
            continue

        digest = await build_weekly_digest(session, parent_email, now=now)
        if digest is None:
            summary["skipped_quiet"] += 1
            continue

        await sender.send(
            session,
            to=parent_email,
            template="weekly_digest",
            context=digest,
        )
        if prefs is None:
            prefs = ParentPreferences(parent_email=parent_email)
            session.add(prefs)
        prefs.last_digest_sent_at = now
        summary["sent"] += 1
        await product_analytics_service.record(
            session,
            "digest_sent",
            user=None,
            role="parent",
            props={"surface": "weekly_digest", "variant": premium_variant(parent_email)},
        )

    await session.commit()
    return summary
