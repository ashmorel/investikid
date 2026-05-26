"""Make tutor_conversations.lesson_id nullable for standalone coach.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-05-26

"""
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column(
        "tutor_conversations",
        "lesson_id",
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "tutor_conversations",
        "lesson_id",
        nullable=False,
    )
