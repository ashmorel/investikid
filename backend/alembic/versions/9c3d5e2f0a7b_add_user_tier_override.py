"""per-child tier override on users

Revision ID: 9c3d5e2f0a7b
Revises: 8b2f4c1d9e6a
Create Date: 2026-06-11 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c3d5e2f0a7b"
down_revision: str | None = "8b2f4c1d9e6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tier_override", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "tier_override")
