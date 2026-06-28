"""concept taxonomy — concepts table + concept_id FKs on lessons and weak_concepts

Revision ID: a0b1c2d3e4f5
Revises: f8a9b0c1d2e3
Create Date: 2026-06-28 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a0b1c2d3e4f5"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create concepts table
    op.create_table(
        "concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.String(30), nullable=False),
        sa.Column("slug", sa.String(60), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("blurb", sa.String(400), nullable=True),
        sa.Column("difficulty_tier", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_concepts_topic", "concepts", ["topic"])
    op.create_unique_constraint("uq_concepts_slug", "concepts", ["slug"])

    # 2. Add concept_id nullable FK on lessons
    op.add_column(
        "lessons",
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_lessons_concept_id", "lessons", ["concept_id"])
    op.create_foreign_key(
        "fk_lessons_concept_id",
        "lessons",
        "concepts",
        ["concept_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 3. Add concept_id nullable FK on weak_concepts
    op.add_column(
        "weak_concepts",
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_weak_concepts_concept_id", "weak_concepts", ["concept_id"])
    op.create_foreign_key(
        "fk_weak_concepts_concept_id",
        "weak_concepts",
        "concepts",
        ["concept_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # Drop FKs and columns on weak_concepts
    op.drop_constraint("fk_weak_concepts_concept_id", "weak_concepts", type_="foreignkey")
    op.drop_index("ix_weak_concepts_concept_id", table_name="weak_concepts")
    op.drop_column("weak_concepts", "concept_id")

    # Drop FKs and columns on lessons
    op.drop_constraint("fk_lessons_concept_id", "lessons", type_="foreignkey")
    op.drop_index("ix_lessons_concept_id", table_name="lessons")
    op.drop_column("lessons", "concept_id")

    # Drop concepts table (indexes/constraints drop with it)
    op.drop_index("ix_concepts_topic", table_name="concepts")
    op.drop_constraint("uq_concepts_slug", "concepts", type_="unique")
    op.drop_table("concepts")
