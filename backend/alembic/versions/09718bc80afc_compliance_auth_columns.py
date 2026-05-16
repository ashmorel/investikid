"""compliance auth columns

Revision ID: 09718bc80afc
Revises: 5b9ed6eec8c9
Create Date: 2026-05-16 14:49:43.582266

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '09718bc80afc'
down_revision: str | None = '5b9ed6eec8c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_purged_at", "users", ["purged_at"])
    op.add_column("users", sa.Column("profiling_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("marketing_opt_in", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("policy_version_accepted", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("policy_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "policy_accepted_at")
    op.drop_column("users", "policy_version_accepted")
    op.drop_column("users", "marketing_opt_in")
    op.drop_column("users", "profiling_enabled")
    op.drop_index("ix_users_purged_at", table_name="users")
    op.drop_column("users", "purged_at")
    op.drop_column("users", "email_verified_at")
