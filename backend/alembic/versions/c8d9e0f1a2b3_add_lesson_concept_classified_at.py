"""add lesson concept_classified_at

Adds a nullable timezone-aware datetime column ``concept_classified_at`` to
the ``lessons`` table. The classifier sets this on every lesson it processes
(tagged, skipped, or unmatched) so that re-runs never re-attempt already-seen
lessons, making the drain loop strictly monotonic.

Revision ID: c8d9e0f1a2b3
Revises: c7e9a1b3d5f7
Create Date: 2026-06-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c8d9e0f1a2b3"
down_revision = "c7e9a1b3d5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column("concept_classified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lessons", "concept_classified_at")
