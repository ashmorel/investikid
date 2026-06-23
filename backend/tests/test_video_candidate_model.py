import pytest
from sqlalchemy import select

from app.models.content import VideoCandidate

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_video_candidate_persists_with_defaults(db_session):
    c = VideoCandidate(
        youtube_id="abc123", title="Compound interest explained",
        source="recovered", market_code="GB", origin_context="saving / Old Saving Module",
    )
    db_session.add(c)
    await db_session.flush()
    got = (await db_session.scalars(select(VideoCandidate))).one()
    assert got.status == "pending"          # server default
    assert got.embeddable is None
    assert got.suggested_module_id is None
    assert got.created_at is not None
