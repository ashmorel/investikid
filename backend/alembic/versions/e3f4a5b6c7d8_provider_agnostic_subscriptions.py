"""provider-agnostic subscriptions + premium_request.declined_at

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
import sqlalchemy as sa

from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="stripe"),
    )
    op.add_column("subscriptions", sa.Column("external_id", sa.String(length=255), nullable=True))
    # Drop the original single-column unique constraints (auto-named by Postgres);
    # uniqueness now lives on the composite (provider, external_id).
    op.drop_constraint("subscriptions_stripe_customer_id_key", "subscriptions", type_="unique")
    op.drop_constraint("subscriptions_stripe_subscription_id_key", "subscriptions", type_="unique")
    op.alter_column("subscriptions", "stripe_customer_id", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("subscriptions", "stripe_subscription_id", existing_type=sa.String(length=255), nullable=True)
    op.execute(
        "UPDATE subscriptions SET external_id = stripe_subscription_id "
        "WHERE stripe_subscription_id IS NOT NULL"
    )
    op.create_index("ix_subscriptions_provider", "subscriptions", ["provider"])
    op.create_index("ix_subscriptions_external_id", "subscriptions", ["external_id"])
    op.create_unique_constraint(
        "uq_subscriptions_provider_external_id", "subscriptions", ["provider", "external_id"]
    )
    op.add_column(
        "premium_requests", sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column("subscriptions", "provider", server_default=None)


def downgrade() -> None:
    op.drop_column("premium_requests", "declined_at")
    op.drop_constraint("uq_subscriptions_provider_external_id", "subscriptions", type_="unique")
    op.drop_index("ix_subscriptions_external_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_provider", table_name="subscriptions")
    op.alter_column("subscriptions", "stripe_subscription_id", existing_type=sa.String(length=255), nullable=True)
    op.alter_column("subscriptions", "stripe_customer_id", existing_type=sa.String(length=255), nullable=False)
    op.create_unique_constraint(
        "subscriptions_stripe_subscription_id_key", "subscriptions", ["stripe_subscription_id"]
    )
    op.create_unique_constraint(
        "subscriptions_stripe_customer_id_key", "subscriptions", ["stripe_customer_id"]
    )
    op.drop_column("subscriptions", "external_id")
    op.drop_column("subscriptions", "provider")
