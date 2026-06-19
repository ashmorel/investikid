"""market_briefs table

Revision ID: e4a7b2c1d0f3
Revises: d3f6a9c0b1e2
Create Date: 2026-06-19
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "e4a7b2c1d0f3"
down_revision = "d3f6a9c0b1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_briefs",
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("brief_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="draft"),
        sa.Column("model_used", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["market_code"], ["markets.code"]),
        sa.PrimaryKeyConstraint("market_code"),
    )


def downgrade() -> None:
    op.drop_table("market_briefs")
