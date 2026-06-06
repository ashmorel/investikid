"""add leaderboard groups + memberships

Revision ID: f7a8b9c0d1e2
Revises: a1b2c3d4e5f7
Create Date: 2026-06-05 14:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leaderboard_groups",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("owner_parent_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaderboard_groups_code", "leaderboard_groups", ["code"], unique=True)
    op.create_index("ix_leaderboard_groups_owner_parent_email", "leaderboard_groups", ["owner_parent_email"])
    op.create_table(
        "group_memberships",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("added_by_parent_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["leaderboard_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_membership"),
    )
    op.create_index("ix_group_memberships_group_id", "group_memberships", ["group_id"])
    op.create_index("ix_group_memberships_user_id", "group_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_group_memberships_user_id", table_name="group_memberships")
    op.drop_index("ix_group_memberships_group_id", table_name="group_memberships")
    op.drop_table("group_memberships")
    op.drop_index("ix_leaderboard_groups_owner_parent_email", table_name="leaderboard_groups")
    op.drop_index("ix_leaderboard_groups_code", table_name="leaderboard_groups")
    op.drop_table("leaderboard_groups")
