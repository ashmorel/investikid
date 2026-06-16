"""revise XP daily cap counters on user_progress

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-06-16 20:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e2f3a4b5c6d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Per-day revise XP tally (mirrors sim_xp_date/sim_xp_today) so revision XP
    # is daily-capped and can't be farmed via repeatable refreshers.
    op.add_column("user_progress", sa.Column("revise_xp_date", sa.Date(), nullable=True))
    op.add_column(
        "user_progress",
        sa.Column("revise_xp_today", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("user_progress", "revise_xp_today")
    op.drop_column("user_progress", "revise_xp_date")
