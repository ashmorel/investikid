"""B3 — arcade-subordination invariant (pure, no DB/async)."""
from __future__ import annotations

from app.services import arcade_service as svc


def test_arcade_cap_subordination_invariant():
    """The arcade is a small *capped* coin source so that LEARNING (uncapped lesson
    coins) always out-earns play. Keep this cap low — well under a day's lesson-earning
    potential. Bumping it past ~a single lesson's reward erodes the rule; a change here
    is intentional and must update the arcade-subordination rule in AGENTS.md.
    """
    assert svc.ARCADE_DAILY_XP_CAP == 25
