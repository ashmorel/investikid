from datetime import date
from typing import Sequence

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


def streak_after_activity(
    last: date | None, current: int, today: date
) -> tuple[int, date]:
    """Return (new_streak_count, new_last_activity_date) after an activity today.

    - First ever activity → streak = 1
    - Same day as last activity → no change
    - Exactly the next day → increment
    - Any other gap → reset to 1
    """
    if last is None:
        return 1, today
    if last == today:
        return current, today
    if (today - last).days == 1:
        return current + 1, today
    return 1, today


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
