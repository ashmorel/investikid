"""replace dead compound-interest YouTube video

The seeded video MqZmwQoHmAA ("Compound interest explained simply") was deleted
on YouTube, so the lesson showed YouTube's "Video unavailable". Repoint it to a
live, embeddable replacement (Khan Academy "Compound interest introduction").

Runs before `python -m app.seed.run` on deploy, so the seed (which matches video
lessons by `video:{youtube_id}` identity) finds the updated row and does not
create a duplicate. Idempotent: the WHERE clause no-ops if the dead id is absent.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-05

"""
from collections.abc import Sequence

from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_ID = "MqZmwQoHmAA"
_NEW_ID = "Rm6UdfRs3gw"


def _repoint(from_id: str, to_id: str) -> None:
    # content_json is a JSON column; cast to jsonb to merge the key, then back.
    op.execute(
        f"""
        UPDATE lessons
        SET content_json = (
            content_json::jsonb || jsonb_build_object('youtube_id', '{to_id}')
        )::json
        WHERE type = 'video' AND content_json->>'youtube_id' = '{from_id}'
        """
    )


def upgrade() -> None:
    _repoint(_OLD_ID, _NEW_ID)


def downgrade() -> None:
    _repoint(_NEW_ID, _OLD_ID)
