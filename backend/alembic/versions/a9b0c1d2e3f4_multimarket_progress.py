"""multi-market progress: user_market_progress + active_market_code + weak_concept market (C2a)

Revision ID: a9b0c1d2e3f4
Revises: c2d3e4f5a6b7
Create Date: 2026-06-18 16:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

from alembic import op

revision: str = "a9b0c1d2e3f4"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_market_progress",
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.PrimaryKeyConstraint("user_id", "market_code"),
    )
    op.create_index("ix_user_market_progress_user_id", "user_market_progress", ["user_id"])

    # Backfill: every user gets a GB row = their current global XP (all current
    # content is GB, so sum(per-market) == UserProgress.xp holds post-migration).
    op.execute(
        """
        INSERT INTO user_market_progress (user_id, market_code, xp, created_at)
        SELECT u.id, 'GB', COALESCE(up.xp, 0), now()
        FROM users u
        LEFT JOIN user_progress up ON up.user_id = u.id
        """
    )

    op.add_column(
        "users",
        sa.Column("active_market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_users_active_market", "users", "markets", ["active_market_code"], ["code"])

    op.add_column(
        "weak_concepts",
        sa.Column("market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_weak_concepts_market", "weak_concepts", "markets", ["market_code"], ["code"])
    op.create_index("ix_weak_concepts_market_code", "weak_concepts", ["market_code"])


def downgrade() -> None:
    op.drop_index("ix_weak_concepts_market_code", table_name="weak_concepts")
    op.drop_constraint("fk_weak_concepts_market", "weak_concepts", type_="foreignkey")
    op.drop_column("weak_concepts", "market_code")
    op.drop_constraint("fk_users_active_market", "users", type_="foreignkey")
    op.drop_column("users", "active_market_code")
    op.drop_index("ix_user_market_progress_user_id", table_name="user_market_progress")
    op.drop_table("user_market_progress")
