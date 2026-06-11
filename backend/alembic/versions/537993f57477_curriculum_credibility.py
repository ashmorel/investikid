"""curriculum credibility: standards/sources/objectives JSON + level_mastery + backfill

Revision ID: 537993f57477
Revises: 3737143bb340
Create Date: 2026-06-11 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "537993f57477"
down_revision: str | None = "3737143bb340"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BACKFILL_SQL = """
INSERT INTO level_mastery (id, user_id, level_id, mastered_at, score)
SELECT gen_random_uuid(),
       agg.user_id,
       agg.level_id,
       agg.mastered_at,
       COALESCE(agg.avg_score, agg.pass_threshold)
FROM (
    SELECT lc.user_id,
           l.level_id,
           lv.pass_threshold,
           COUNT(*) AS completed_count,
           AVG(lc.score) AS avg_score,
           MAX(lc.completed_at) AS mastered_at
    FROM lesson_completions lc
    JOIN lessons l ON l.id = lc.lesson_id AND l.level_id IS NOT NULL
    JOIN levels lv ON lv.id = l.level_id
    GROUP BY lc.user_id, l.level_id, lv.pass_threshold
) agg
JOIN (
    SELECT level_id, COUNT(*) AS total_lessons
    FROM lessons
    WHERE level_id IS NOT NULL
    GROUP BY level_id
) totals ON totals.level_id = agg.level_id
WHERE agg.completed_count = totals.total_lessons
  AND (agg.avg_score IS NULL OR agg.avg_score >= agg.pass_threshold)
"""


def upgrade() -> None:
    op.add_column("modules", sa.Column("standards_alignment", sa.JSON(), nullable=True))
    op.add_column("modules", sa.Column("sources", sa.JSON(), nullable=True))
    op.add_column("levels", sa.Column("learning_objectives", sa.JSON(), nullable=True))

    op.create_table(
        "level_mastery",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("level_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mastered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "level_id", name="uq_level_mastery_user_level"),
    )
    op.create_index("ix_level_mastery_user_id", "level_mastery", ["user_id"])
    op.create_index("ix_level_mastery_level_id", "level_mastery", ["level_id"])

    # Backfill: a level is mastered when the user completed ALL of its lessons
    # and the average of non-null scores meets the pass threshold (or no
    # lessons were scored at all). Mirrors level_service._complete_and_passed.
    op.execute(sa.text(BACKFILL_SQL))


def downgrade() -> None:
    op.drop_index("ix_level_mastery_level_id", table_name="level_mastery")
    op.drop_index("ix_level_mastery_user_id", table_name="level_mastery")
    op.drop_table("level_mastery")
    op.drop_column("levels", "learning_objectives")
    op.drop_column("modules", "sources")
    op.drop_column("modules", "standards_alignment")
