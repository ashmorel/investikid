"""add spaced repetition items table

Revision ID: e4f5a6b7c8d9
Revises: 9b7815c040
Create Date: 2026-05-22 23:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "9b7815c040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spaced_repetition_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("weak_concept_id", sa.Uuid(), nullable=False),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("repetition_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["weak_concept_id"], ["weak_concepts.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "weak_concept_id", name="uq_sr_user_concept"),
    )
    op.create_index("ix_sr_user_next_review", "spaced_repetition_items", ["user_id", "next_review_at"])


def downgrade() -> None:
    op.drop_index("ix_sr_user_next_review", table_name="spaced_repetition_items")
    op.drop_table("spaced_repetition_items")
