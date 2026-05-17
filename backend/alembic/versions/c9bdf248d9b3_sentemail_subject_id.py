"""add subject_id column to sent_emails (close cross-child export IDOR)

Revision ID: c9bdf248d9b3
Revises: 09718bc80afc
Create Date: 2026-05-17 17:41:11.199145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9bdf248d9b3'
down_revision: Union[str, None] = '09718bc80afc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import sqlalchemy as sa
    op.add_column("sent_emails", sa.Column("subject_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_sent_emails_subject_id"), "sent_emails", ["subject_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sent_emails_subject_id"), table_name="sent_emails")
    op.drop_column("sent_emails", "subject_id")
