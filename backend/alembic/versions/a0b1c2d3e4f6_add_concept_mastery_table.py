"""add concept_mastery table

Revision ID: a0b1c2d3e4f6
Revises: f9a0b1c2d3e4
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a0b1c2d3e4f6"
down_revision: str | None = "f9a0b1c2d3e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concept_mastery",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "mastery_score", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column(
            "last_attempt_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "concept_id"),
        sa.UniqueConstraint(
            "user_id", "concept_id", name="uq_concept_mastery_user_concept"
        ),
    )


def downgrade() -> None:
    op.drop_table("concept_mastery")
