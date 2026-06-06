"""premium_request table"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "premium_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("child_user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_email", sa.String(320), nullable=False),
        sa.Column("context_kind", sa.String(20), nullable=False),
        sa.Column("context_label", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_premium_requests_child_user_id", "premium_requests", ["child_user_id"])
    op.create_index("ix_premium_requests_parent_email", "premium_requests", ["parent_email"])
    op.create_index("ix_premium_requests_created_at", "premium_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_premium_requests_created_at", table_name="premium_requests")
    op.drop_index("ix_premium_requests_parent_email", table_name="premium_requests")
    op.drop_index("ix_premium_requests_child_user_id", table_name="premium_requests")
    op.drop_table("premium_requests")
