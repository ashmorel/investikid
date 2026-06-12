"""cosmetics tables + learning-coin backfill (M8)

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-12 19:50:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cosmetic_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(length=40), nullable=False, unique=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("emoji", sa.String(length=8), nullable=False, server_default="🎁"),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("coin_cost", sa.Integer(), nullable=False),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "user_cosmetics",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cosmetic_items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("equipped", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Retroactive learning coins: kids start the shop with coins matching the
    # XP they have already earned (the earn rule is 1 coin per XP from now on).
    op.execute("UPDATE user_progress SET virtual_coins = xp WHERE virtual_coins = 0")


def downgrade() -> None:
    op.drop_table("user_cosmetics")
    op.drop_table("cosmetic_items")
