"""Validates the data-migration SQL that repoints the dead compound-interest
video, against real Postgres (the migration itself is only run on deploy, since
CI builds the schema with create_all rather than `alembic upgrade head`)."""
import pytest
from sqlalchemy import text

from app.models.content import Lesson, Level, Module

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Mirrors alembic/versions/c9d0e1f2a3b4_replace_dead_compound_interest_video.py,
# which interpolates the (constant, trusted) ids as SQL literals — this also
# sidesteps asyncpg's inability to infer the type of a bare bind param inside
# jsonb_build_object.
_REPOINT_SQL = text(
    """
    UPDATE lessons
    SET content_json = (
        content_json::jsonb || jsonb_build_object('youtube_id', 'Rm6UdfRs3gw')
    )::json
    WHERE type = 'video' AND content_json->>'youtube_id' = 'MqZmwQoHmAA'
    """
)


async def test_repoint_sql_updates_only_the_dead_video(db_session):
    module = Module(topic="savings", title="CI Repoint Mod", country_codes=[],
                    is_premium=False, order_index=0, icon="📈")
    db_session.add(module)
    await db_session.flush()
    level = Level(module_id=module.id, title="L1", order_index=0,
                 is_premium=False, pass_threshold=0.7)
    db_session.add(level)
    await db_session.flush()

    dead = Lesson(module_id=module.id, level_id=level.id, type="video", order_index=0,
                  xp_reward=10, content_json={"youtube_id": "MqZmwQoHmAA", "caption": "x"})
    other = Lesson(module_id=module.id, level_id=level.id, type="video", order_index=1,
                   xp_reward=10, content_json={"youtube_id": "p7HKvqRI_Bo", "caption": "y"})
    db_session.add_all([dead, other])
    await db_session.flush()

    await db_session.execute(_REPOINT_SQL)
    await db_session.flush()
    await db_session.refresh(dead)
    await db_session.refresh(other)

    # dead video repointed; its other fields preserved; unrelated video untouched.
    assert dead.content_json["youtube_id"] == "Rm6UdfRs3gw"
    assert dead.content_json["caption"] == "x"
    assert other.content_json["youtube_id"] == "p7HKvqRI_Bo"
