"""market curriculum proposal

Revision ID: b2d4f6a8c0e1
Revises: e4a7b2c1d0f3
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "b2d4f6a8c0e1"
down_revision = "e4a7b2c1d0f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_curriculum_proposal",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="proposed"),
        sa.Column("proposal_json", sa.JSON(), nullable=False),
        sa.Column("coverage_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_market_curriculum_proposal_market_code",
        "market_curriculum_proposal",
        ["market_code"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_curriculum_proposal_market_code",
        table_name="market_curriculum_proposal",
    )
    op.drop_table("market_curriculum_proposal")
