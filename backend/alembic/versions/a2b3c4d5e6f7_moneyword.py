"""moneyword: word bank + daily schedule + daily play tables

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-23 20:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- arcade_words ---
    op.create_table(
        "arcade_words",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("word", sa.String(length=8), nullable=False),
        sa.Column("definition", sa.String(length=200), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
        sa.Column("length", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("word", "language", name="uq_arcade_word_lang"),
    )
    op.create_index("ix_arcade_words_language", "arcade_words", ["language"])
    op.create_index("ix_arcade_words_status", "arcade_words", ["status"])

    # --- arcade_daily_schedule ---
    op.create_table(
        "arcade_daily_schedule",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("puzzle_date", sa.Date(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("word_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["word_id"], ["arcade_words.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("puzzle_date", "language", name="uq_arcade_daily_date_lang"),
    )
    op.create_index("ix_arcade_daily_schedule_puzzle_date", "arcade_daily_schedule", ["puzzle_date"])

    # --- arcade_daily_play ---
    op.create_table(
        "arcade_daily_play",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("puzzle_date", sa.Date(), nullable=False),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("guesses", JSON(), nullable=False, server_default="[]"),
        sa.Column("solved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "puzzle_date", name="uq_arcade_daily_play_user_date"),
    )
    op.create_index("ix_arcade_daily_play_user_id", "arcade_daily_play", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_arcade_daily_play_user_id", table_name="arcade_daily_play")
    op.drop_table("arcade_daily_play")
    op.drop_index("ix_arcade_daily_schedule_puzzle_date", table_name="arcade_daily_schedule")
    op.drop_table("arcade_daily_schedule")
    op.drop_index("ix_arcade_words_status", table_name="arcade_words")
    op.drop_index("ix_arcade_words_language", table_name="arcade_words")
    op.drop_table("arcade_words")
