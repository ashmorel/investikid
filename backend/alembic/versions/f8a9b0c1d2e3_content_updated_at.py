"""content updated_at for offline delta

Revision ID: f8a9b0c1d2e3
Revises: e6f7a8b9c0d1
Create Date: 2026-06-28 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("modules", "levels", "lessons"):
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    op.create_index("ix_lessons_updated_at", "lessons", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_lessons_updated_at", table_name="lessons")
    for table in ("modules", "levels", "lessons"):
        op.drop_column(table, "updated_at")
