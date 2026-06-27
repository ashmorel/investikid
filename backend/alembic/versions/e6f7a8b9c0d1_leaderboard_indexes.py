"""leaderboard scale: partial index for public board population + lesson_completions.lesson_id

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-06-27 10:00:00.000000

Adds two indexes that remove full-table scans from the weekly leaderboard:
  - ``ix_users_lb_market`` — partial index over ``users(active_market_code)``
    restricted to the public board population (consented, non-hidden). Serves
    both market scope (range scan) and global scope (partial-index scan).
  - ``ix_lesson_completions_lesson_id`` — the XP metric joins Lesson on
    ``lesson_completions.lesson_id``, which previously had no standalone index
    (only the composite ``(user_id, lesson_id)`` unique constraint, whose
    leading column is user_id and so can't serve a lesson_id-only join).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: str | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_users_lb_market",
        "users",
        ["active_market_code"],
        postgresql_where=sa.text("leaderboard_consent AND NOT leaderboard_hidden"),
    )
    op.create_index(
        "ix_lesson_completions_lesson_id",
        "lesson_completions",
        ["lesson_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_completions_lesson_id", table_name="lesson_completions")
    op.drop_index("ix_users_lb_market", table_name="users")
