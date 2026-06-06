"""simulator integration: apply missions, cash grants, sim xp, module cash reward"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c1d2e3f4a5b6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apply_missions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_type", sa.String(30), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("prompt", sa.String(300), nullable=False),
        sa.Column("xp_reward", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cash_reward", sa.Numeric(12, 2), nullable=True),
        sa.Column("badge_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("badges.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("lesson_id", name="uq_apply_mission_lesson"),
    )
    op.create_table(
        "apply_mission_completions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("apply_missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "mission_id", name="uq_apply_mission_completion_user_mission"),
    )
    op.create_index("ix_apply_mission_completions_user_id", "apply_mission_completions", ["user_id"])
    op.create_index("ix_apply_mission_completions_mission_id", "apply_mission_completions", ["mission_id"])
    op.create_table(
        "cash_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "source_type", "source_id", name="uq_cash_grant_source"),
    )
    op.create_index("ix_cash_grants_user_id", "cash_grants", ["user_id"])
    op.add_column("user_progress", sa.Column("sim_xp_date", sa.Date(), nullable=True))
    op.add_column("user_progress",
                  sa.Column("sim_xp_today", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("modules", sa.Column("completion_cash_reward", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "completion_cash_reward")
    op.drop_column("user_progress", "sim_xp_today")
    op.drop_column("user_progress", "sim_xp_date")
    op.drop_index("ix_cash_grants_user_id", table_name="cash_grants")
    op.drop_table("cash_grants")
    op.drop_index("ix_apply_mission_completions_mission_id", table_name="apply_mission_completions")
    op.drop_index("ix_apply_mission_completions_user_id", table_name="apply_mission_completions")
    op.drop_table("apply_mission_completions")
    op.drop_table("apply_missions")
