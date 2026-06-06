"""Single source of truth for leaderboard-group tunables."""

GROUP_SIZE_CAP = 30          # max children per group
GROUPS_PER_PARENT_CAP = 10   # max groups one parent may own
GROUP_CODE_LENGTH = 8        # join-code length
# Unambiguous alphabet (no O/0, I/1, L) for shareable codes.
GROUP_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LEADERBOARD_WEEK_START_WEEKDAY = 0  # Monday — weekly window reset (matches global board)
