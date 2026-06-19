"""market rewards: reward-state columns, badge.market_code, market badges + GB backfill

Revision ID: b1d4e5f6a7c8
Revises: a9b0c1d2e3f4
Create Date: 2026-06-19
"""
import sqlalchemy as sa

from alembic import op

revision = "b1d4e5f6a7c8"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None

_MARKET_BADGES = [
    ("GB", "United Kingdom", "🇬🇧"), ("US", "United States", "🇺🇸"),
    ("AU", "Australia", "🇦🇺"), ("CA", "Canada", "🇨🇦"),
    ("IE", "Ireland", "🇮🇪"), ("ES", "Spain", "🇪🇸"),
    ("FR", "France", "🇫🇷"), ("DE", "Germany", "🇩🇪"),
    ("HK", "Hong Kong", "🇭🇰"), ("SG", "Singapore", "🇸🇬"),
]


def upgrade() -> None:
    op.add_column("user_market_progress", sa.Column("enroll_rewarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user_market_progress", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "user_market_progress",
        sa.Column("completion_rewarded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("badges", sa.Column("market_code", sa.String(length=2), nullable=True))
    op.create_foreign_key("fk_badges_market_code", "badges", "markets", ["market_code"], ["code"])

    conn = op.get_bind()
    # Seed the 10 market badges (idempotent by name).
    for code, name, flag in _MARKET_BADGES:
        badge_name = f"Market Mastered: {name}"
        exists = conn.execute(sa.text("SELECT id FROM badges WHERE name = :n"), {"n": badge_name}).first()
        if exists is None:
            conn.execute(sa.text(
                "INSERT INTO badges (id, name, description, icon_url, condition_type, condition_value, market_code) "
                "VALUES (gen_random_uuid(), :n, :d, :i, 'market_completed', 0, :c)"
            ), {"n": badge_name, "d": f"Finish all the {name} money lessons", "i": flag, "c": code})

    # Backfill: GB completers get the GB badge (NO coins) + stamps. A user has
    # "completed GB" iff GB has >=1 lesson and they completed every GB lesson.
    gb_badge = conn.execute(sa.text(
        "SELECT id FROM badges WHERE name = 'Market Mastered: United Kingdom'"
    )).scalar()
    gb_total = conn.execute(sa.text(
        "SELECT COUNT(*) FROM lessons l JOIN modules m ON m.id = l.module_id WHERE m.market_code = 'GB'"
    )).scalar() or 0
    if gb_badge is not None and gb_total > 0:
        # users who completed all GB lessons
        rows = conn.execute(sa.text(
            "SELECT lc.user_id "
            "FROM lesson_completions lc "
            "JOIN lessons l ON l.id = lc.lesson_id "
            "JOIN modules m ON m.id = l.module_id "
            "WHERE m.market_code = 'GB' "
            "GROUP BY lc.user_id "
            "HAVING COUNT(DISTINCT lc.lesson_id) >= :total"
        ), {"total": gb_total}).fetchall()
        for (user_id,) in rows:
            # badge (skip if already owned)
            owned = conn.execute(sa.text(
                "SELECT 1 FROM user_badges WHERE user_id = :u AND badge_id = :b"
            ), {"u": user_id, "b": gb_badge}).first()
            if owned is None:
                conn.execute(sa.text(
                    "INSERT INTO user_badges (user_id, badge_id, earned_at) VALUES (:u, :b, NOW())"
                ), {"u": user_id, "b": gb_badge})
            # stamp the GB market-progress row if present (no coins)
            conn.execute(sa.text(
                "UPDATE user_market_progress SET completed_at = NOW(), completion_rewarded_at = NOW() "
                "WHERE user_id = :u AND market_code = 'GB'"
            ), {"u": user_id})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "DELETE FROM user_badges WHERE badge_id IN "
        "(SELECT id FROM badges WHERE condition_type = 'market_completed')"
    ))
    conn.execute(sa.text("DELETE FROM badges WHERE condition_type = 'market_completed'"))
    op.drop_constraint("fk_badges_market_code", "badges", type_="foreignkey")
    op.drop_column("badges", "market_code")
    op.drop_column("user_market_progress", "completion_rewarded_at")
    op.drop_column("user_market_progress", "completed_at")
    op.drop_column("user_market_progress", "enroll_rewarded_at")
