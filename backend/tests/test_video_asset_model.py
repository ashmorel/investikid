from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models.video_asset import VideoAsset

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_video_asset_roundtrips(db_session):
    a = VideoAsset(storage_key="videos/abc.mp4", content_type="video/mp4",
                   size_bytes=1234, original_filename="lesson.mp4", created_at=datetime.now(UTC))
    db_session.add(a)
    await db_session.flush()
    got = await db_session.scalar(select(VideoAsset).where(VideoAsset.storage_key == "videos/abc.mp4"))
    assert got is not None
    assert got.content_type == "video/mp4"
    assert got.size_bytes == 1234
