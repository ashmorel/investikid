"""module published flag

Revision ID: c3e5a7b9d1f2
Revises: b2d4f6a8c0e1
"""
import sqlalchemy as sa
from alembic import op

revision = "c3e5a7b9d1f2"
down_revision = "b2d4f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "modules",
        sa.Column("published", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("modules", "published")
