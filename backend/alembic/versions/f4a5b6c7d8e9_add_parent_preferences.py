"""add parent_preferences

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-06-07

"""
import sqlalchemy as sa

from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parent_preferences",
        sa.Column("parent_email", sa.String(length=255), nullable=False),
        sa.Column(
            "trial_reminder_opt_out",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("parent_email"),
    )


def downgrade() -> None:
    op.drop_table("parent_preferences")
