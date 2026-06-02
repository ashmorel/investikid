"""add lesson_views table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-02 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_views",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", UUID(as_uuid=True), nullable=False),
        sa.Column("first_viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_view_user_lesson"),
    )
    op.create_index("ix_lesson_views_user_id", "lesson_views", ["user_id"])
    op.create_index("ix_lesson_views_lesson_id", "lesson_views", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_views_lesson_id", table_name="lesson_views")
    op.drop_index("ix_lesson_views_user_id", table_name="lesson_views")
    op.drop_table("lesson_views")
