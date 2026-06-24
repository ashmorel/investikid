"""leaderboard: display_handle + consent + hidden on users

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-06-24 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_handle", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("leaderboard_consent", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("leaderboard_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_users_display_handle", "users", ["display_handle"])


def downgrade() -> None:
    op.drop_constraint("uq_users_display_handle", "users", type_="unique")
    op.drop_column("users", "leaderboard_hidden")
    op.drop_column("users", "leaderboard_consent")
    op.drop_column("users", "display_handle")
