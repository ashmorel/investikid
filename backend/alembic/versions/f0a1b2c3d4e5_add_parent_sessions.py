"""add parent_sessions table

Revision ID: f0a1b2c3d4e5
Revises: e1f2a3b4c5d6
Create Date: 2026-06-05 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "parent_sessions",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("jti", UUID(as_uuid=True), nullable=False),
        sa.Column("parent_email", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_parent_sessions_jti", "parent_sessions", ["jti"], unique=True)
    op.create_index(
        "ix_parent_sessions_parent_email", "parent_sessions", ["parent_email"]
    )


def downgrade() -> None:
    op.drop_index("ix_parent_sessions_parent_email", table_name="parent_sessions")
    op.drop_index("ix_parent_sessions_jti", table_name="parent_sessions")
    op.drop_table("parent_sessions")
