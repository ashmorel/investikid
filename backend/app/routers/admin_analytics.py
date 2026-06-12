"""Admin product-analytics summary (M4).

The ONLY read surface for ``analytics_events`` (with product_analytics_service).
Pure SQL aggregates — counts and funnels, never per-child browsing.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.analytics import AnalyticsEvent
from app.models.user import User
from app.routers.admin_auth import get_current_admin

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])

_COHORT_WEEKS = 8


def _pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(100 * numerator / denominator, 1)


async def _count_events(session: AsyncSession, name: str, since: datetime) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(AnalyticsEvent)
            .where(AnalyticsEvent.event_name == name, AnalyticsEvent.occurred_at >= since)
        )
    ) or 0


def _active_between(user: type[User], start_offset: timedelta, end_offset: timedelta):
    """EXISTS: any event for the user inside [created_at+start, created_at+end)."""
    return exists().where(
        and_(
            AnalyticsEvent.user_id == user.id,
            AnalyticsEvent.occurred_at >= user.created_at + start_offset,
            AnalyticsEvent.occurred_at < user.created_at + end_offset,
        )
    )


@router.get("/summary")
async def analytics_summary(
    days: int = Query(default=30, ge=1, le=180),
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    # --- Activation: signups in window with a lesson_completed within 24h ---
    signups = (
        await session.scalar(
            select(func.count()).select_from(User).where(User.created_at >= since)
        )
    ) or 0
    activated = (
        await session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= since, _active_lesson_within_24h())
        )
    ) or 0

    # --- Weekly signup cohorts with D7 / D30 retention ---
    cohort_since = now - timedelta(weeks=_COHORT_WEEKS)
    week = func.date_trunc("week", User.created_at).label("week")
    cohort_rows = (
        await session.execute(
            select(
                week,
                func.count().label("signups"),
                func.count()
                .filter(_active_between(User, timedelta(days=7), timedelta(days=14)))
                .label("d7"),
                func.count()
                .filter(_active_between(User, timedelta(days=28), timedelta(days=35)))
                .label("d30"),
            )
            .where(User.created_at >= cohort_since)
            .group_by(week)
            .order_by(week)
        )
    ).all()
    cohorts = [
        {
            "week_start": row.week.date().isoformat(),
            "signups": row.signups,
            "d7_pct": _pct(row.d7, row.signups),
            "d30_pct": _pct(row.d30, row.signups),
        }
        for row in cohort_rows
    ]

    # --- Funnel + engagement counts ---
    funnel = {
        name: await _count_events(session, name, since)
        for name in ("paywall_view", "trial_started", "subscription_activated")
    }
    home_view = await _count_events(session, "home_view", since)
    home_cta_tap = await _count_events(session, "home_cta_tap", since)

    surface = AnalyticsEvent.props["surface"].as_string().label("surface")
    quicklink_rows = (
        await session.execute(
            select(surface, func.count())
            .where(
                AnalyticsEvent.event_name == "quicklink_tap",
                AnalyticsEvent.occurred_at >= since,
            )
            .group_by(surface)
        )
    ).all()

    return {
        "window_days": days,
        "activation": {
            "signups": signups,
            "activated": activated,
            "rate_pct": _pct(activated, signups),
        },
        "cohorts": cohorts,
        "funnel": funnel,
        "engagement": {
            "home_view": home_view,
            "home_cta_tap": home_cta_tap,
            "cta_through_pct": _pct(home_cta_tap, home_view),
            "quicklink_taps": {surface: count for surface, count in quicklink_rows if surface},
            "lesson_completed": await _count_events(session, "lesson_completed", since),
            "digest_sent": await _count_events(session, "digest_sent", since),
        },
    }


def _active_lesson_within_24h():
    return exists().where(
        and_(
            AnalyticsEvent.user_id == User.id,
            AnalyticsEvent.event_name == "lesson_completed",
            AnalyticsEvent.occurred_at <= User.created_at + timedelta(hours=24),
            AnalyticsEvent.occurred_at >= User.created_at,
        )
    )
