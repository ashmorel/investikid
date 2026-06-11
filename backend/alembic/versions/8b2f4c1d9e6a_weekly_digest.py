"""weekly digest: parent prefs opt-out + last-sent, module conversation_prompt

Revision ID: 8b2f4c1d9e6a
Revises: 537993f57477
Create Date: 2026-06-11 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8b2f4c1d9e6a"
down_revision: str | None = "537993f57477"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "parent_preferences",
        sa.Column(
            "weekly_digest_opt_out",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "parent_preferences",
        sa.Column("last_digest_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "modules",
        sa.Column("conversation_prompt", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("modules", "conversation_prompt")
    op.drop_column("parent_preferences", "last_digest_sent_at")
    op.drop_column("parent_preferences", "weekly_digest_opt_out")
