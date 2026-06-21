from collections.abc import Sequence
from datetime import date

from app.services.streak_config import (
    STREAK_FREEZE_CAP,
    STREAK_FREEZE_GAP,
    STREAK_MILESTONE,
)

# XP thresholds per level (index = level-1 → threshold to reach NEXT level).
# Exponential-ish curve from the spec: Piggy Bank (1) → ... → Investment Pro (7).
_LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2500, 5000]


def compute_level(xp: int) -> int:
    """Return level number (1-7) for the given total XP. Capped at 7."""
    level = 1
    for idx, threshold in enumerate(_LEVEL_THRESHOLDS, start=1):
        if xp >= threshold:
            level = idx
    return level


def content_region_for(user) -> str:
    """Effective *learning region* used for module-country gating.

    Returns the child's chosen ``content_region`` (US/GB/HK), falling back to
    their legal ``country_code`` when unset (NULL). Uses ``getattr`` so it works
    on any object exposing ``country_code`` and avoids importing the User model.

    NEVER mutate ``country_code`` from region features — it drives the
    COPPA/UK-GDPR consent regime (compliance.py / consent_service.py).
    """
    return getattr(user, "content_region", None) or user.country_code


def is_module_accessible(
    user_country: str,
    is_premium_user: bool,
    module_country_codes: Sequence[str],
    module_is_premium: bool,
) -> bool:
    """A module is accessible if:
    - country_codes is empty (global) OR user's country is listed, AND
    - module is free OR user is premium.
    """
    country_ok = not module_country_codes or user_country in module_country_codes
    premium_ok = (not module_is_premium) or is_premium_user
    return country_ok and premium_ok


def is_module_in_market(module_market_code: str, home_market_code: str) -> bool:
    """C1 single-market gate: a module is in scope when it belongs to the user's
    home market. (Multi-market enrollment arrives in Sub-project C2.)"""
    return module_market_code == home_market_code


def is_module_visible(module, active_market_code: str) -> bool:
    """Child-facing visibility: a module is shown only when it is published AND
    in the user's active market. Staged (unpublished) modules — built by the
    curriculum engine before an atomic publish — are invisible to children."""
    return bool(module.published) and is_module_in_market(module.market_code, active_market_code)


def is_module_premium_ok(*, module_is_premium: bool, is_premium_user: bool) -> bool:
    """Premium gate, decoupled from the (now market-based) region gate."""
    return (not module_is_premium) or is_premium_user


def is_module_age_ok(
    user_age: int,
    module_min_age: int | None,
    module_max_age: int | None,
) -> bool:
    """Age gate for module browse/access (mirrors recommendation_service's hard filter).

    A module is age-appropriate if the user's actual age (from dob — NEVER the
    parent tier_override) is >= min_age and <= max_age, treating None as unbounded.
    """
    if module_min_age is not None and user_age < module_min_age:
        return False
    if module_max_age is not None and user_age > module_max_age:
        return False
    return True


def _grant_milestone(streak: int, freezes: int) -> int:
    """Grant one freeze (capped) when the streak hits a milestone."""
    if streak % STREAK_MILESTONE == 0:
        return min(STREAK_FREEZE_CAP, freezes + 1)
    return freezes


def streak_after_activity(
    last: date | None, current: int, freezes: int, today: date
) -> tuple[int, date, int]:
    """Return (new_streak, new_last_activity_date, new_freezes) after an activity today.

    - First ever activity -> streak = 1.
    - Same day as last activity -> no change.
    - Exactly the next day -> increment; milestone may grant a freeze.
    - Exactly one missed day (gap == STREAK_FREEZE_GAP) with a freeze available ->
      consume one freeze, continue the streak (milestone re-checked on the new value).
    - Any larger gap, or a missed day with no freeze -> reset to 1 (freezes unchanged).
    - A date earlier than the last activity (clock skew) -> no change.
    """
    if last is None:
        return 1, today, freezes
    if last == today:
        return current, today, freezes
    gap = (today - last).days
    if gap < 0:
        # Clock skew / backwards date — don't punish a real streak; keep the later date.
        return current, last, freezes
    if gap == 1:
        new = current + 1
        return new, today, _grant_milestone(new, freezes)
    if gap == STREAK_FREEZE_GAP and freezes > 0:
        new = current + 1
        return new, today, _grant_milestone(new, freezes - 1)
    return 1, today, freezes


def record_daily_activity(progress, today_local: date) -> bool:
    """Advance the streak for the first qualifying activity of the day (lesson or trade).

    Idempotent: a no-op if the user already had activity today. Returns True if the streak
    was advanced this call, False if it was already counted today.
    """
    if progress.last_activity_date == today_local:
        return False
    new_streak, new_last, new_freezes = streak_after_activity(
        progress.last_activity_date, progress.streak_count, progress.streak_freezes, today_local
    )
    progress.streak_count = new_streak
    progress.last_activity_date = new_last
    progress.streak_freezes = new_freezes
    return True


def derive_lesson_title(lesson_type: str, content_json: dict) -> str:
    """Derive a human-readable lesson title from content_json by type."""
    if lesson_type == "card":
        return content_json.get("title") or "Card lesson"
    if lesson_type == "quiz":
        return content_json.get("question") or "Quiz"
    if lesson_type == "scenario":
        return content_json.get("prompt") or "Scenario"
    if lesson_type == "video":
        return content_json.get("caption") or "Video lesson"
    return "Lesson"


async def grant_module_completion_cash(session, user_id, module_id) -> bool:
    """Grant a module's completion_cash_reward once, iff every lesson in the module is done.

    Returns True if cash was granted this call, else False. Idempotent via the CashGrant ledger.
    """
    from sqlalchemy import func, select

    from app.models.content import Lesson, LessonCompletion, Module
    from app.models.simulator import Portfolio
    from app.services.simulator_rewards import grant_cash

    module = await session.get(Module, module_id)
    if module is None or module.completion_cash_reward is None:
        return False

    total = await session.scalar(
        select(func.count(Lesson.id)).where(Lesson.module_id == module_id)
    )
    if not total:
        return False
    done = await session.scalar(
        select(func.count(func.distinct(LessonCompletion.lesson_id)))
        .select_from(LessonCompletion)
        .join(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(Lesson.module_id == module_id, LessonCompletion.user_id == user_id)
    )
    if (done or 0) < total:
        return False

    portfolio = await session.scalar(select(Portfolio).where(Portfolio.user_id == user_id))
    if portfolio is None:
        return False
    return await grant_cash(
        session, user_id, portfolio, "module", module_id, module.completion_cash_reward
    )
