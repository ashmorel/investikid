"""add variant_key to generated_content (4b content variety)

Revision ID: a1b2c3d4e5f6
Revises: c9bdf248d9b3
Create Date: 2026-05-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "c9bdf248d9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_UQ = "uq_generated_content_lesson_concept_model"
_NEW_UQ = "uq_generated_content_lesson_concept_model_variant"


def upgrade() -> None:
    op.add_column(
        "generated_content",
        sa.Column("variant_key", sa.String(length=16),
                  nullable=False, server_default="core:0"),
    )
    op.drop_constraint(_OLD_UQ, "generated_content", type_="unique")
    op.create_unique_constraint(
        _NEW_UQ, "generated_content",
        ["lesson_id", "concept", "model_used", "variant_key"],
    )


def downgrade() -> None:
    op.drop_constraint(_NEW_UQ, "generated_content", type_="unique")
    op.create_unique_constraint(
        _OLD_UQ, "generated_content",
        ["lesson_id", "concept", "model_used"],
    )
    op.drop_column("generated_content", "variant_key")
