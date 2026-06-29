"""add mastery_checkpoints, mastery_checkpoint_topics, diagnostic_sessions

Revision ID: c9d8e7f6a5b4
Revises: 9a8b7c6d5e4f
Create Date: 2026-06-29 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "c9d8e7f6a5b4"
down_revision: str | None = "9a8b7c6d5e4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- mastery_checkpoints ---
    op.create_table(
        "mastery_checkpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("market_code", sa.String(8), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column(
            "session_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column(
            "taken_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_mastery_checkpoints_user_id",
        "mastery_checkpoints",
        ["user_id"],
    )

    # --- mastery_checkpoint_topics (child; CASCADE from mastery_checkpoints) ---
    op.create_table(
        "mastery_checkpoint_topics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "checkpoint_id",
            UUID(as_uuid=True),
            sa.ForeignKey("mastery_checkpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(30), nullable=False),
        sa.Column("correct", sa.Integer, nullable=False),
        sa.Column("attempted", sa.Integer, nullable=False),
    )
    op.create_index(
        "ix_mastery_checkpoint_topics_checkpoint_id",
        "mastery_checkpoint_topics",
        ["checkpoint_id"],
    )

    # --- diagnostic_sessions ---
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("market_code", sa.String(8), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("item_ids", JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_diagnostic_sessions_user_id",
        "diagnostic_sessions",
        ["user_id"],
    )


def downgrade() -> None:
    # Drop child table before parent
    op.drop_index("ix_mastery_checkpoint_topics_checkpoint_id", table_name="mastery_checkpoint_topics")
    op.drop_table("mastery_checkpoint_topics")

    op.drop_index("ix_mastery_checkpoints_user_id", table_name="mastery_checkpoints")
    op.drop_table("mastery_checkpoints")

    op.drop_index("ix_diagnostic_sessions_user_id", table_name="diagnostic_sessions")
    op.drop_table("diagnostic_sessions")
