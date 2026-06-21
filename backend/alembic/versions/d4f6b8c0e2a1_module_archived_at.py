"""module archived_at + backfill genuinely-retired modules

Revision ID: d4f6b8c0e2a1
Revises: c3e5a7b9d1f2
Create Date: 2026-06-21

Adds modules.archived_at (NULL = active; set = archived). Backfills it for
genuinely-retired modules: published=false AND not referenced by any active
(proposed/accepted/published) curriculum proposal. Staged in-progress modules
(which ARE in an accepted proposal) stay active.
"""
from alembic import op
import sqlalchemy as sa

revision = "d4f6b8c0e2a1"
down_revision = "c3e5a7b9d1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_modules_archived_at", "modules", ["archived_at"])
    op.execute(
        """
        UPDATE modules SET archived_at = now()
        WHERE published = false
          AND NOT EXISTS (
            SELECT 1 FROM market_curriculum_proposal p,
                 jsonb_array_elements((p.proposal_json)::jsonb->'modules') m
            WHERE p.status IN ('proposed','accepted','published')
              AND (m->>'module_id')::uuid = modules.id
          )
        """
    )


def downgrade() -> None:
    op.drop_index("ix_modules_archived_at", table_name="modules")
    op.drop_column("modules", "archived_at")
