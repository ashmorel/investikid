"""add lesson_drafts

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-06-08

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: str | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lesson_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("level_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("content_json", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("concept", sa.String(length=200), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column("moderation_safe", sa.Boolean(), nullable=False),
        sa.Column("moderation_category", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lesson_drafts_level_id", "lesson_drafts", ["level_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_drafts_level_id", table_name="lesson_drafts")
    op.drop_table("lesson_drafts")
