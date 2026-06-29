"""add verifier columns to diagnostic_items

Revision ID: e7f8a9b0c1d2
Revises: c9d8e7f6a5b4
Create Date: 2026-06-29 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "c9d8e7f6a5b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnostic_items",
        sa.Column("verifier_status", sa.String(12), nullable=True),
    )
    op.add_column(
        "diagnostic_items",
        sa.Column("verifier_answer_index", sa.Integer, nullable=True),
    )
    op.add_column(
        "diagnostic_items",
        sa.Column("verifier_note", sa.Text, nullable=True),
    )
    op.add_column(
        "diagnostic_items",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("diagnostic_items", "verified_at")
    op.drop_column("diagnostic_items", "verifier_note")
    op.drop_column("diagnostic_items", "verifier_answer_index")
    op.drop_column("diagnostic_items", "verifier_status")
