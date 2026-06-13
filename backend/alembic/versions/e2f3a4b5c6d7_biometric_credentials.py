"""biometric credentials + users.biometric_allowed (SP-Bio)

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-06-13 10:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e2f3a4b5c6d7"
down_revision: str | None = "d1e2f3a4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("biometric_allowed", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "biometric_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_kind", sa.String(length=10), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("parent_email", sa.String(length=255), nullable=True),
        sa.Column("subject_key", sa.String(length=80), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=60), nullable=False),
        sa.Column("secret_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("device_id", "subject_key", name="uq_biometric_device_subject"),
    )
    op.create_index("ix_biometric_credentials_user_id", "biometric_credentials", ["user_id"])
    op.create_index("ix_biometric_credentials_parent_email", "biometric_credentials", ["parent_email"])
    op.create_index("ix_biometric_credentials_subject_key", "biometric_credentials", ["subject_key"])
    op.create_index("ix_biometric_credentials_secret_hash", "biometric_credentials", ["secret_hash"])


def downgrade() -> None:
    op.drop_table("biometric_credentials")
    op.drop_column("users", "biometric_allowed")
