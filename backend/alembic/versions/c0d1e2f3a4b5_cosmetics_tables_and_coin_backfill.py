"""cosmetics catalog columns + learning-coin backfill (M8)

Both cosmetics tables have existed since the initial schema (6bdd8c950985) —
the models predate the feature. This migration only ALIGNS `cosmetic_items`
with the M8 catalog (slug + emoji) and backfills learning coins.

Revision ID: c0d1e2f3a4b5
Revises: b9c0d1e2f3a4
Create Date: 2026-06-12 19:50:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c0d1e2f3a4b5"
down_revision: str | None = "b9c0d1e2f3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # slug: add nullable, defensively backfill any pre-existing rows (none are
    # expected — the feature never shipped), then tighten to NOT NULL + unique.
    op.add_column("cosmetic_items", sa.Column("slug", sa.String(length=40), nullable=True))
    op.execute(
        "UPDATE cosmetic_items SET slug = lower(replace(name, ' ', '_')) WHERE slug IS NULL"
    )
    op.alter_column("cosmetic_items", "slug", nullable=False)
    op.create_unique_constraint("uq_cosmetic_items_slug", "cosmetic_items", ["slug"])

    op.add_column(
        "cosmetic_items",
        sa.Column("emoji", sa.String(length=8), nullable=False, server_default="🎁"),
    )

    # Retroactive learning coins: kids start the shop with coins matching the
    # XP they have already earned (the earn rule is 1 coin per XP from now on).
    op.execute("UPDATE user_progress SET virtual_coins = xp WHERE virtual_coins = 0")


def downgrade() -> None:
    op.drop_constraint("uq_cosmetic_items_slug", "cosmetic_items", type_="unique")
    op.drop_column("cosmetic_items", "emoji")
    op.drop_column("cosmetic_items", "slug")
