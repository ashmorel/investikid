"""daily goal columns + push registry (M7)

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-12 18:10:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: str | None = "a8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_progress",
        sa.Column("daily_goal_xp", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "user_progress",
        sa.Column("xp_today", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("user_progress", sa.Column("xp_today_date", sa.Date(), nullable=True))
    op.add_column(
        "user_progress", sa.Column("last_push_sent_date", sa.Date(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "push_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_push_devices_user_id", "push_devices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_push_devices_user_id", table_name="push_devices")
    op.drop_table("push_devices")
    op.drop_column("users", "push_enabled")
    op.drop_column("user_progress", "last_push_sent_date")
    op.drop_column("user_progress", "xp_today_date")
    op.drop_column("user_progress", "xp_today")
    op.drop_column("user_progress", "daily_goal_xp")
