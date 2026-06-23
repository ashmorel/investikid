"""add video_candidates review queue

Revision ID: e7c1a2b3d4f5
Revises: d4f6b8c0e2a1
Create Date: 2026-06-23 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "e7c1a2b3d4f5"
down_revision: str | None = "d4f6b8c0e2a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_candidates",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("youtube_id", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=12), nullable=False),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("origin_context", sa.String(length=300), nullable=True),
        sa.Column("suggested_module_id", UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_level_id", UUID(as_uuid=True), nullable=True),
        sa.Column("embeddable", sa.Boolean(), nullable=True),
        sa.Column("health_detail", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="pending", nullable=False),
        sa.Column("created_lesson_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.ForeignKeyConstraint(["suggested_module_id"], ["modules.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_level_id"], ["levels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_lesson_id"], ["lessons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("youtube_id", "market_code", name="uq_video_candidate_video_market"),
    )
    op.create_index("ix_video_candidates_market_code", "video_candidates", ["market_code"])
    op.create_index("ix_video_candidates_status", "video_candidates", ["status"])


def downgrade() -> None:
    op.drop_index("ix_video_candidates_status", table_name="video_candidates")
    op.drop_index("ix_video_candidates_market_code", table_name="video_candidates")
    op.drop_table("video_candidates")
