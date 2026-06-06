"""Single source of truth for the age-tier (derived live from DOB; never stored)."""
from datetime import date
from typing import Literal

AGE_TIER_BOUNDARY = 14  # age (inclusive) at which a learner becomes "investor"

AgeTier = Literal["explorer", "investor"]


def age_in_years(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def age_tier(dob: date, today: date) -> AgeTier:
    return "investor" if age_in_years(dob, today) >= AGE_TIER_BOUNDARY else "explorer"


# LLM register directives — the ONE place to retune tone per tier.
AGE_REGISTER_DIRECTIVE: dict[AgeTier, str] = {
    "explorer": (
        "The learner is 10-13. Be warm, playful, simple and encouraging; "
        "at most one light emoji; avoid jargon."
    ),
    "investor": (
        "The learner is 14-18. Be encouraging but mature and concise; no baby-talk; "
        "minimal or no emoji; you may use real financial terms."
    ),
}
