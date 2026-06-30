"""Single source of truth for streak / streak-freeze tunables.

Product rules (not secrets) — change here to retune; ships with a backend deploy,
no app release. Promote to env-driven Settings later if per-env tuning is ever needed.
"""

STREAK_MILESTONE = 7    # earn a freeze each time the streak hits a multiple of this
STREAK_FREEZE_CAP = 2   # max freezes a user can hold
STREAK_FREEZE_GAP = 2   # a day-gap of exactly this (= 1 missed day) is freezable

# Coin-funded streak repair (B6): spend earned coins to revive a just-lapsed streak.
STREAK_REPAIR_COST = 50       # flat coin cost to repair
STREAK_REPAIR_MAX_GAP = 3     # repair offered only while last activity is within this many days
STREAK_REPAIR_MIN_STREAK = 3  # only worth repairing a streak this long or longer
