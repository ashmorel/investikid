"""users.started_market_code (nullable) + backfill to dominant market

Revision ID: d3f6a9c0b1e2
Revises: c2e5f8a9b0c1
Create Date: 2026-06-19
"""
import sqlalchemy as sa

from alembic import op

revision = "d3f6a9c0b1e2"
down_revision = "c2e5f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("started_market_code", sa.String(length=2), nullable=True))
    op.create_foreign_key(
        "fk_users_started_market_code", "users", "markets", ["started_market_code"], ["code"]
    )
    # Backfill: each user's dominant market = the UserMarketProgress row with the
    # most XP (tie-break earliest created_at). Today this resolves to GB for all.
    op.execute(sa.text(
        "UPDATE users SET started_market_code = sub.market_code "
        "FROM ("
        "  SELECT DISTINCT ON (user_id) user_id, market_code "
        "  FROM user_market_progress "
        "  ORDER BY user_id, xp DESC, created_at ASC"
        ") sub "
        "WHERE users.id = sub.user_id AND users.started_market_code IS NULL"
    ))


def downgrade() -> None:
    op.drop_constraint("fk_users_started_market_code", "users", type_="foreignkey")
    op.drop_column("users", "started_market_code")
