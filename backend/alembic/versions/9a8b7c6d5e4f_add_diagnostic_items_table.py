"""add diagnostic_items table

Additive migration that creates the diagnostic_items table for the A2 Unit 1
calibrated diagnostic assessment engine.  Items carry market/topic/concept
tags, a difficulty tier, question/choices/answer payload, and telemetry
counters used for adaptive calibration.

Revision ID: 9a8b7c6d5e4f
Revises: c8d9e0f1a2b3
Create Date: 2026-06-29
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

from alembic import op

revision: str = "9a8b7c6d5e4f"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("market_code", sa.String(8), nullable=False),
        sa.Column("topic", sa.String(30), nullable=False),
        sa.Column(
            "concept_id",
            UUID(as_uuid=True),
            sa.ForeignKey("concepts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # difficulty_tier: 1 = beginner, 2 = intermediate, 3 = advanced
        sa.Column("difficulty_tier", sa.Integer, nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("choices", JSON, nullable=False),
        sa.Column("answer_index", sa.Integer, nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
        # status values: draft / approved / retired
        sa.Column(
            "status",
            sa.String(12),
            nullable=False,
            server_default="draft",
        ),
        # source values: generated / authored
        sa.Column("source", sa.String(12), nullable=False),
        sa.Column(
            "times_shown",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "times_correct",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Individual column indexes
    op.create_index(
        "ix_diagnostic_items_market_code",
        "diagnostic_items",
        ["market_code"],
    )
    op.create_index(
        "ix_diagnostic_items_concept_id",
        "diagnostic_items",
        ["concept_id"],
    )
    op.create_index(
        "ix_diagnostic_items_status",
        "diagnostic_items",
        ["status"],
    )
    # Composite index for the common query pattern: items by market + topic + status
    op.create_index(
        "ix_diagnostic_items_market_topic_status",
        "diagnostic_items",
        ["market_code", "topic", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_diagnostic_items_market_topic_status", table_name="diagnostic_items")
    op.drop_index("ix_diagnostic_items_status", table_name="diagnostic_items")
    op.drop_index("ix_diagnostic_items_concept_id", table_name="diagnostic_items")
    op.drop_index("ix_diagnostic_items_market_code", table_name="diagnostic_items")
    op.drop_table("diagnostic_items")
