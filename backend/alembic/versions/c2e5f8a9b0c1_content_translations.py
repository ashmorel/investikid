"""content_translations table

Revision ID: c2e5f8a9b0c1
Revises: b1d4e5f6a7c8
Create Date: 2026-06-19
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "c2e5f8a9b0c1"
down_revision = "b1d4e5f6a7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=10), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("translated_json", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(length=10), nullable=False, server_default="auto"),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("entity_type", "entity_id", "language", name="uq_content_translation"),
    )
    op.create_index("ix_content_translation_type_lang", "content_translations", ["entity_type", "language"])


def downgrade() -> None:
    op.drop_index("ix_content_translation_type_lang", table_name="content_translations")
    op.drop_table("content_translations")
