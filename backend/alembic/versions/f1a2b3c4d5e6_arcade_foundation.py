"""arcade foundation: scores table + user_progress xp cap columns

Revision ID: f1a2b3c4d5e6
Revises: e7c1a2b3d4f5
Create Date: 2026-06-23 19:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e7c1a2b3d4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "arcade_scores",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("game", sa.String(length=16), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_arcade_scores_user_id", "arcade_scores", ["user_id"])
    op.create_index("ix_arcade_scores_game", "arcade_scores", ["game"])
    op.create_index("ix_arcade_scores_market_code", "arcade_scores", ["market_code"])
    op.add_column("user_progress", sa.Column("arcade_xp_date", sa.Date(), nullable=True))
    op.add_column(
        "user_progress",
        sa.Column("arcade_xp_today", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_progress", "arcade_xp_today")
    op.drop_column("user_progress", "arcade_xp_date")
    op.drop_index("ix_arcade_scores_market_code", table_name="arcade_scores")
    op.drop_index("ix_arcade_scores_game", table_name="arcade_scores")
    op.drop_index("ix_arcade_scores_user_id", table_name="arcade_scores")
    op.drop_table("arcade_scores")
