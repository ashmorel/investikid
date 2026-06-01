"""add levels and lessons.level_id with Level 1 backfill

Revision ID: b1c2d3e4f5a6
Revises: f6a7b8c9d0e1
Create Date: 2026-06-01 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "levels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("is_premium", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pass_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("content_source", sa.String(length=16), nullable=False, server_default="authored"),
        sa.Column("icon", sa.String(length=10), nullable=False, server_default="📊"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_levels_module_id", "levels", ["module_id"])

    op.add_column("lessons", sa.Column("level_id", sa.Uuid(), nullable=True))
    op.create_index("ix_lessons_level_id", "lessons", ["level_id"])
    op.create_foreign_key(
        "fk_lessons_level_id", "lessons", "levels", ["level_id"], ["id"], ondelete="CASCADE"
    )

    # Backfill: one "Level 1" per module, inheriting is_premium; attach its lessons.
    conn = op.get_bind()
    modules = conn.execute(sa.text("SELECT id, is_premium FROM modules")).fetchall()
    for module_id, is_premium in modules:
        level_id = conn.execute(
            sa.text(
                "INSERT INTO levels (id, module_id, title, order_index, is_premium, "
                "pass_threshold, content_source, icon, created_at) "
                "VALUES (gen_random_uuid(), :mid, 'Level 1', 0, :prem, 0.7, 'authored', '📊', now()) "
                "RETURNING id"
            ),
            {"mid": module_id, "prem": is_premium},
        ).scalar_one()
        conn.execute(
            sa.text("UPDATE lessons SET level_id = :lid WHERE module_id = :mid"),
            {"lid": level_id, "mid": module_id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_lessons_level_id", "lessons", type_="foreignkey")
    op.drop_index("ix_lessons_level_id", table_name="lessons")
    op.drop_column("lessons", "level_id")
    op.drop_index("ix_levels_module_id", table_name="levels")
    op.drop_table("levels")
