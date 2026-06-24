"""collectables: availability window + rarity + unlock rule on cosmetic_items

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-06-24 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op as op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cosmetic_items", sa.Column("available_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cosmetic_items", sa.Column("available_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("cosmetic_items", sa.Column("rarity", sa.String(length=12), nullable=True))
    op.add_column("cosmetic_items", sa.Column("unlock_type", sa.String(length=20), nullable=True))
    op.add_column("cosmetic_items", sa.Column("unlock_threshold", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("cosmetic_items", "unlock_threshold")
    op.drop_column("cosmetic_items", "unlock_type")
    op.drop_column("cosmetic_items", "rarity")
    op.drop_column("cosmetic_items", "available_until")
    op.drop_column("cosmetic_items", "available_from")
