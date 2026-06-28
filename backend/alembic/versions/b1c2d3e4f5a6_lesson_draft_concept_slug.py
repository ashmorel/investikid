"""lesson_draft concept_slug column

Adds a nullable concept_slug column to lesson_drafts so that the LLM
generation pipeline can store the concept slug it emitted for later
resolution to concept_id at approval time.

Revision ID: b1c2d3e4f5a6
Revises: a0b1c2d3e4f5
Create Date: 2026-06-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b1c2d3e4f5a6"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lesson_drafts",
        sa.Column("concept_slug", sa.String(60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lesson_drafts", "concept_slug")
