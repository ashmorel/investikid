"""Single source of truth for streak / streak-freeze tunables.

Product rules (not secrets) — change here to retune; ships with a backend deploy,
no app release. Promote to env-driven Settings later if per-env tuning is ever needed.
"""

STREAK_MILESTONE = 7    # earn a freeze each time the streak hits a multiple of this
STREAK_FREEZE_CAP = 2   # max freezes a user can hold
STREAK_FREEZE_GAP = 2   # a day-gap of exactly this (= 1 missed day) is freezable
