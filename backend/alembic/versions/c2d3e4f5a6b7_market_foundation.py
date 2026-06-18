"""market foundation: markets table + module/user market codes (C1)

Revision ID: c2d3e4f5a6b7
Revises: b0c1d2e3f4a5
Create Date: 2026-06-18 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MARKETS = [
    {"code": "GB", "name": "United Kingdom", "currency_code": "GBP",
     "default_language": "en", "has_content": True, "is_active": True},
    {"code": "US", "name": "United States", "currency_code": "USD",
     "default_language": "en", "has_content": False, "is_active": True},
    {"code": "AU", "name": "Australia", "currency_code": "AUD",
     "default_language": "en", "has_content": False, "is_active": True},
    {"code": "CA", "name": "Canada", "currency_code": "CAD",
     "default_language": "en", "has_content": False, "is_active": True},
    {"code": "IE", "name": "Ireland", "currency_code": "EUR",
     "default_language": "en", "has_content": False, "is_active": True},
    {"code": "ES", "name": "Spain", "currency_code": "EUR",
     "default_language": "es", "has_content": False, "is_active": True},
    {"code": "FR", "name": "France", "currency_code": "EUR",
     "default_language": "fr", "has_content": False, "is_active": True},
    {"code": "DE", "name": "Germany", "currency_code": "EUR",
     "default_language": "de", "has_content": False, "is_active": True},
    {"code": "HK", "name": "Hong Kong", "currency_code": "HKD",
     "default_language": "en", "has_content": False, "is_active": True},
    {"code": "SG", "name": "Singapore", "currency_code": "SGD",
     "default_language": "en", "has_content": False, "is_active": True},
]


def upgrade() -> None:
    markets = op.create_table(
        "markets",
        sa.Column("code", sa.String(length=2), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("default_language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("has_content", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.bulk_insert(markets, _MARKETS)

    op.add_column(
        "modules",
        sa.Column("market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_modules_market", "modules", "markets", ["market_code"], ["code"])
    op.create_index("ix_modules_market_code", "modules", ["market_code"])

    op.add_column(
        "users",
        sa.Column("home_market_code", sa.String(length=2), nullable=False, server_default="GB"),
    )
    op.create_foreign_key("fk_users_home_market", "users", "markets", ["home_market_code"], ["code"])


def downgrade() -> None:
    op.drop_constraint("fk_users_home_market", "users", type_="foreignkey")
    op.drop_column("users", "home_market_code")
    op.drop_index("ix_modules_market_code", table_name="modules")
    op.drop_constraint("fk_modules_market", "modules", type_="foreignkey")
    op.drop_column("modules", "market_code")
    op.drop_table("markets")
