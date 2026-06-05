import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_presign_requires_admin(client):
    r = await client.post("/admin/video-assets/presign",
                          json={"filename": "a.mp4", "content_type": "video/mp4", "size_bytes": 100})
    assert r.status_code in (401, 403)


async def test_presign_503_when_unconfigured(admin_client, monkeypatch):
    import app.routers.admin as admin_mod
    monkeypatch.setattr(admin_mod.storage, "is_configured", lambda: False)
    r = await admin_client.post("/admin/video-assets/presign",
                                json={"filename": "a.mp4", "content_type": "video/mp4", "size_bytes": 100})
    assert r.status_code == 503
    assert r.json()["detail"] == "not_configured"


async def test_presign_rejects_non_mp4(admin_client, monkeypatch):
    import app.routers.admin as admin_mod
    monkeypatch.setattr(admin_mod.storage, "is_configured", lambda: True)
    r = await admin_client.post("/admin/video-assets/presign",
                                json={"filename": "a.mov", "content_type": "video/quicktime", "size_bytes": 100})
    assert r.status_code == 422 or r.status_code == 400


async def test_presign_ok_creates_asset(admin_client, db_session, monkeypatch):
    import app.routers.admin as admin_mod
    monkeypatch.setattr(admin_mod.storage, "is_configured", lambda: True)
    monkeypatch.setattr(admin_mod.storage, "create_presigned_put", lambda key, ct, expires=900: "https://r2/PUT")
    monkeypatch.setattr(admin_mod.storage, "public_url", lambda key: f"https://cdn/{key}")
    r = await admin_client.post("/admin/video-assets/presign",
                                json={"filename": "lesson.mp4", "content_type": "video/mp4", "size_bytes": 1000})
    assert r.status_code == 200
    body = r.json()
    assert body["upload_url"] == "https://r2/PUT"
    assert body["public_url"].startswith("https://cdn/videos/")
    assert body["key"].startswith("videos/") and body["key"].endswith(".mp4")

    from sqlalchemy import select

    from app.models.video_asset import VideoAsset
    asset = await db_session.scalar(select(VideoAsset).where(VideoAsset.storage_key == body["key"]))
    assert asset is not None and asset.content_type == "video/mp4"


def test_video_content_validation_hosted_vs_youtube():
    from pydantic import ValidationError

    from app.schemas.admin import LessonCreate

    # youtube source (default) still requires youtube_id
    with pytest.raises(ValidationError):
        LessonCreate(type="video", xp_reward=15, order_index=0,
                     content_json={"video_source": "youtube"})
    # hosted requires video_url
    with pytest.raises(ValidationError):
        LessonCreate(type="video", xp_reward=15, order_index=0,
                     content_json={"video_source": "hosted"})
    # hosted with video_url is valid
    LessonCreate(type="video", xp_reward=15, order_index=0,
                 content_json={"video_source": "hosted", "video_url": "https://cdn/videos/x.mp4"})
