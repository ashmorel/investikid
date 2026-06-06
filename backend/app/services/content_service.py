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
