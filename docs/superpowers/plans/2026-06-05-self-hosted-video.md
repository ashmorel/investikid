# Self-Hosted Curated Video (Cloudflare R2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let admins upload curated MP4 lesson videos to our own Cloudflare R2 bucket (via presigned direct upload) and have children play them inline (ad-free, no 153) as a per-lesson alternative to YouTube.

**Architecture:** The browser requests a short-lived presigned PUT URL from the backend (boto3 → R2 S3 endpoint) and uploads the file straight to R2; the lesson's `content_json` stores `video_source:"hosted"` + the public CDN `video_url`; the child `VideoLesson` renders an HTML5 `<video playsinline>`. Feature-gated: when `R2_*` env is unset, upload returns `503 not_configured` and the YouTube path is unaffected.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + boto3 (new dep) (backend); React 18 + Vite + TS + TanStack Query + Tailwind v4 + Vitest/vitest-axe (frontend).

---

## Reference facts (verified — read before starting)

- **Spec:** `invest-ed/docs/superpowers/specs/2026-06-05-self-hosted-video-design.md`.
- **Alembic head:** `d0e1f2a3b4c5` (verify: nothing chains from it). New migration chains from it. `alembic upgrade head` may hang locally → rely on CI; verify chain via grep.
- **boto3 is NOT yet a dependency** — add `boto3==1.34.69` (or latest 1.34.x) to `backend/requirements.txt` in Task 1.
- **Config** (`app/core/config.py`): pydantic `BaseSettings`, flat fields with `""` defaults for optional secrets (e.g. `stripe_secret_key: str = ""`). Add the R2 fields the same way. (Confirm the exact class + whether it reads from env/.env — it does.)
- **`.env.example`** (`backend/.env.example`) lists all env vars — add the R2 ones (never touch `.env`).
- **Admin video validation** (`app/schemas/admin.py` ~L89-91): `elif lesson_type == "video": if not isinstance(v.get("youtube_id"), str) or not v["youtube_id"]: raise ValueError(...)`. This is inside a `LessonCreate`/`LessonBase` `content_json` validator. Change it to honour `video_source`.
- **Admin LessonForm** (`frontend/src/components/admin/LessonForm.tsx`): video state `youtubeInput`/`videoCaption`; `buildContentJson()` video branch returns `{ youtube_id: extractYoutubeId(youtubeInput), caption: videoCaption }`. `extractYoutubeId` accepts a URL or raw id. Light admin theme.
- **Child player** (`frontend/src/components/child/lesson/VideoLesson.tsx`): reads `contentJson.youtube_id`, builds `buildYouTubeUrls`, renders an iframe + "I watched this" + Mark-complete + caption/transcript. `videoEmbed.ts` is YouTube-only (leave it; used only by the youtube branch).
- **Admin router:** `app/routers/admin.py` — `prefix="/admin"`, `Depends(get_current_admin)`. Add the presign endpoint here.
- **Admin API client:** `frontend/src/api/admin.ts` — `adminFetch<T>(path, init)` + TanStack-Query hooks. Add the presign call + upload helper here.
- **Video-health checker:** `app/services/video_health_service.py::check_all_videos` (from the prior feature) — currently YouTube-oEmbed only; T6 extends it to hosted URLs. The `video_health` table has a `youtube_id` column reused to store the checked identifier.
- **not_configured pattern:** SP-D1 OAuth endpoints return `503` with `{"detail":"not_configured"}` when creds are unset — mirror it.
- **Tests:** async backend tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures. **No real network / no real boto3 calls** — monkeypatch the storage client. Local Postgres may hang → rely on CI. Frontend: QueryClientProvider + vitest-axe conventions; mock `@/api/admin`. Ruff rejects semicolons in tests (split `add(); flush()`).

## Commands

- Backend (from `invest-ed/backend`): test `/Users/leeashmore/Local Repo/.venv/bin/pytest`; lint `/Users/leeashmore/Local Repo/.venv/bin/ruff check .`; install new dep `/Users/leeashmore/Local Repo/.venv/bin/pip install boto3==1.34.69`.
- Frontend (from `invest-ed/frontend`): `npx tsc -b`; `npm run lint` (known-OK warnings: `button.tsx` + `Market.tsx`); `npm test`; `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. NEVER read/modify any `.env`. CI's 6 jobs gate the Railway deploy.

---

## Task 1: R2 config + storage service

**Files:**
- Modify: `invest-ed/backend/requirements.txt` (add boto3)
- Modify: `invest-ed/backend/app/core/config.py` (R2 fields)
- Modify: `invest-ed/backend/.env.example` (document R2 vars)
- Create: `invest-ed/backend/app/services/storage.py`
- Test: `invest-ed/backend/tests/test_storage_service.py`

- [ ] **Step 1: Add boto3 + config fields + .env.example**

In `requirements.txt` add a line: `boto3==1.34.69`. Then install: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pip install boto3==1.34.69`.
In `app/core/config.py`, add (next to the other optional-secret fields):
```python
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""  # e.g. https://videos.investkid.app  (public R2/CDN domain, no trailing slash)
    r2_max_upload_bytes: int = 200 * 1024 * 1024  # 200 MB
```
In `backend/.env.example`, add the same keys (empty values + a short comment that they enable admin video upload; bucket needs public read + CORS PUT from the app origins).

- [ ] **Step 2: Write the failing storage test**

Create `tests/test_storage_service.py`:

```python
from unittest.mock import MagicMock

from app.services import storage


def test_not_configured_when_env_missing(monkeypatch):
    monkeypatch.setattr(storage.settings, "r2_bucket", "")
    assert storage.is_configured() is False


def test_configured_when_env_present(monkeypatch):
    for k, v in {
        "r2_account_id": "acct", "r2_access_key_id": "ak", "r2_secret_access_key": "sk",
        "r2_bucket": "vids", "r2_public_base_url": "https://cdn.example.com",
    }.items():
        monkeypatch.setattr(storage.settings, k, v)
    assert storage.is_configured() is True


def test_public_url_joins_base_and_key(monkeypatch):
    monkeypatch.setattr(storage.settings, "r2_public_base_url", "https://cdn.example.com/")
    assert storage.public_url("videos/abc.mp4") == "https://cdn.example.com/videos/abc.mp4"


def test_create_presigned_put_uses_client(monkeypatch):
    fake = MagicMock()
    fake.generate_presigned_url.return_value = "https://r2.example.com/PUT"
    monkeypatch.setattr(storage, "_client", lambda: fake)
    monkeypatch.setattr(storage.settings, "r2_bucket", "vids")
    url = storage.create_presigned_put("videos/abc.mp4", "video/mp4", expires=900)
    assert url == "https://r2.example.com/PUT"
    args, kwargs = fake.generate_presigned_url.call_args
    assert args[0] == "put_object"
    assert kwargs["Params"]["Bucket"] == "vids"
    assert kwargs["Params"]["Key"] == "videos/abc.mp4"
    assert kwargs["Params"]["ContentType"] == "video/mp4"
    assert kwargs["ExpiresIn"] == 900
```

- [ ] **Step 3: Run it — expect FAIL**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_storage_service.py -v`
Expected: FAIL — `app.services.storage` missing.

- [ ] **Step 4: Implement the storage service**

Create `app/services/storage.py`:

```python
import boto3
from botocore.config import Config

from app.core.config import settings


def is_configured() -> bool:
    return all([
        settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key,
        settings.r2_bucket, settings.r2_public_base_url,
    ])


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def public_url(key: str) -> str:
    return f"{settings.r2_public_base_url.rstrip('/')}/{key.lstrip('/')}"


def create_presigned_put(key: str, content_type: str, expires: int = 900) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.r2_bucket, Key=key)
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_storage_service.py -v`
Expected: 4 passed.

- [ ] **Step 6: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app/services/storage.py app/core/config.py tests/test_storage_service.py
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/requirements.txt invest-ed/backend/app/core/config.py invest-ed/backend/.env.example invest-ed/backend/app/services/storage.py invest-ed/backend/tests/test_storage_service.py
git commit -m "feat(video): R2 storage service + config (boto3 presigned uploads)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `video_asset` model + migration

**Files:**
- Create: `invest-ed/backend/app/models/video_asset.py`
- Modify: `invest-ed/backend/app/models/__init__.py` (re-export, matching the package convention)
- Create: `invest-ed/backend/alembic/versions/e1f2a3b4c5d6_add_video_asset.py`
- Test: `invest-ed/backend/tests/test_video_asset_model.py`

- [ ] **Step 1: Write the failing model test**

Create `tests/test_video_asset_model.py`:

```python
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
```

- [ ] **Step 2: Run — expect ImportError**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_asset_model.py -v`
Expected: FAIL — `cannot import name 'VideoAsset'`.

- [ ] **Step 3: Create the model**

Create `app/models/video_asset.py` (mirror `app/models/video_health.py` conventions — `Base` from `app.core.database`, `UUID` from `sqlalchemy.dialects.postgresql`):

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VideoAsset(Base):
    __tablename__ = "video_asset"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```
Add `from app.models.video_asset import VideoAsset  # noqa: F401` to `app/models/__init__.py` if it re-exports models (it does — Task 1 of the prior feature added VideoHealth there).

- [ ] **Step 4: Run the model test — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_asset_model.py -v`
Expected: PASS.

- [ ] **Step 5: Migration**

Create `alembic/versions/e1f2a3b4c5d6_add_video_asset.py`:

```python
"""add video_asset table

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-05

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_asset",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("storage_key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("video_asset")
```

- [ ] **Step 6: Verify chain + ruff + commit**

Run: `cd invest-ed/backend && grep -rl "down_revision.*d0e1f2a3b4c5" alembic/versions/` (expect only the new file) and ruff on the new files. Then:
```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/models/video_asset.py invest-ed/backend/app/models/__init__.py invest-ed/backend/alembic/versions/e1f2a3b4c5d6_add_video_asset.py invest-ed/backend/tests/test_video_asset_model.py
git commit -m "feat(video): video_asset table + migration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Presign endpoint + hosted-video schema validation

**Files:**
- Modify: `invest-ed/backend/app/schemas/admin.py` (presign request/response + video validation honouring `video_source`)
- Modify: `invest-ed/backend/app/routers/admin.py` (presign endpoint)
- Test: `invest-ed/backend/tests/test_video_assets_admin.py`

- [ ] **Step 1: Write the failing endpoint + validation test**

Create `tests/test_video_assets_admin.py` (use the suite's real `admin_client`/`client` fixtures — mirror a sibling admin test; patch `storage`):

```python
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
```

Also add a schema-validation test (hosted requires video_url) — put it here or in an existing admin-schema test file:

```python
def test_video_content_validation_hosted_vs_youtube():
    from pydantic import ValidationError
    from app.schemas.admin import LessonCreate

    # youtube source (default) still requires youtube_id
    with pytest.raises(ValidationError):
        LessonCreate(type="video", xp_reward=15, content_json={"video_source": "youtube"})
    # hosted requires video_url
    with pytest.raises(ValidationError):
        LessonCreate(type="video", xp_reward=15, content_json={"video_source": "hosted"})
    # hosted with video_url is valid
    LessonCreate(type="video", xp_reward=15,
                 content_json={"video_source": "hosted", "video_url": "https://cdn/videos/x.mp4"})
```
> Adjust `LessonCreate(...)` to the real constructor/fields in `app/schemas/admin.py` (it may be `LessonBase`/require more fields — read it). Keep the three assertions.

- [ ] **Step 2: Run — expect FAIL**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_assets_admin.py -v`
Expected: FAIL — endpoint missing / validation not source-aware.

- [ ] **Step 3: Add schemas + update video validation**

In `app/schemas/admin.py`:
```python
class VideoPresignRequest(BaseModel):
    filename: str = Field(max_length=255)
    content_type: str
    size_bytes: int

    @field_validator("content_type")
    @classmethod
    def only_mp4(cls, v):
        if v != "video/mp4":
            raise ValueError("only video/mp4 is supported")
        return v


class VideoPresignResponse(BaseModel):
    asset_id: uuid.UUID
    key: str
    upload_url: str
    public_url: str
```
Update the video branch of the `content_json` validator:
```python
        elif lesson_type == "video":
            source = v.get("video_source", "youtube")
            if source == "hosted":
                if not isinstance(v.get("video_url"), str) or not v["video_url"]:
                    raise ValueError("hosted video lessons require a non-empty video_url")
            else:
                if not isinstance(v.get("youtube_id"), str) or not v["youtube_id"]:
                    raise ValueError("video lessons require a non-empty youtube_id")
```
(`Field`/`field_validator`/`uuid`/`BaseModel` are imported in this file — confirm; add if missing.)

- [ ] **Step 4: Add the presign endpoint**

In `app/routers/admin.py`, import the storage module + model + schemas + size cap:
```python
from app.services import storage
from app.models.video_asset import VideoAsset
from app.schemas.admin import VideoPresignRequest, VideoPresignResponse
from app.core.config import settings
import uuid
from datetime import UTC, datetime
```
Add the route:
```python
@router.post("/video-assets/presign", response_model=VideoPresignResponse)
async def admin_presign_video(
    payload: VideoPresignRequest,
    session: AsyncSession = Depends(get_session),
):
    if not storage.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "not_configured")
    if payload.size_bytes > settings.r2_max_upload_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "file too large")
    key = f"videos/{uuid.uuid4()}.mp4"
    asset = VideoAsset(
        storage_key=key, content_type=payload.content_type,
        size_bytes=payload.size_bytes, original_filename=payload.filename[:255],
        created_at=datetime.now(UTC),
    )
    session.add(asset)
    await session.commit()
    return VideoPresignResponse(
        asset_id=asset.id, key=key,
        upload_url=storage.create_presigned_put(key, payload.content_type),
        public_url=storage.public_url(key),
    )
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_assets_admin.py -v`
Expected: pass.

- [ ] **Step 6: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/schemas/admin.py invest-ed/backend/app/routers/admin.py invest-ed/backend/tests/test_video_assets_admin.py
git commit -m "feat(video): presign upload endpoint + hosted-source lesson validation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Admin LessonForm — source toggle + upload UI

**Files:**
- Modify: `invest-ed/frontend/src/api/admin.ts` (presign + upload helper + types)
- Modify: `invest-ed/frontend/src/components/admin/LessonForm.tsx`
- Test: `invest-ed/frontend/src/components/admin/__tests__/LessonForm.video.test.tsx`

- [ ] **Step 1: Add the API helper**

In `src/api/admin.ts`:
```typescript
export interface VideoPresignResponse {
  asset_id: string; key: string; upload_url: string; public_url: string;
}

export async function presignVideo(filename: string, contentType: string, sizeBytes: number) {
  return adminFetch<VideoPresignResponse>('/admin/video-assets/presign', {
    method: 'POST',
    body: JSON.stringify({ filename, content_type: contentType, size_bytes: sizeBytes }),
  });
}

// Upload directly to R2 via the presigned PUT (XHR for progress). Resolves on 2xx.
export function uploadToPresigned(url: string, file: File, onProgress?: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', file.type);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100)); };
    xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload failed (${xhr.status})`)));
    xhr.onerror = () => reject(new Error('Upload failed'));
    xhr.send(file);
  });
}
```

- [ ] **Step 2: Write the failing component test**

Create `src/components/admin/__tests__/LessonForm.video.test.tsx` (mirror the existing `LessonForm.test.tsx` setup; mock `@/api/admin`'s `presignVideo`/`uploadToPresigned`). Cover: switching source to "Uploaded" shows the file input; selecting a file calls presign+upload and the form's saved `content_json` carries `video_source:'hosted'` + the returned `video_url`. Keep assertions minimal but real (the exact harness depends on how `LessonForm` exposes submit — read the existing test).

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LessonForm } from '@/components/admin/LessonForm';

vi.mock('@/api/admin', async (orig) => {
  const actual = await orig<typeof import('@/api/admin')>();
  return {
    ...actual,
    presignVideo: vi.fn().mockResolvedValue({ asset_id: 'a1', key: 'videos/x.mp4', upload_url: 'https://r2/PUT', public_url: 'https://cdn/videos/x.mp4' }),
    uploadToPresigned: vi.fn().mockResolvedValue(undefined),
  };
});

describe('LessonForm hosted video', () => {
  it('uploads a file and records a hosted video_url', async () => {
    const onSubmit = vi.fn();
    // Render LessonForm with type=video preselected (match the real props/wrapper from LessonForm.test.tsx).
    render(<LessonForm onSubmit={onSubmit} /* ...required props... */ />);
    // switch type to video if needed, then source to Uploaded
    await userEvent.click(screen.getByRole('radio', { name: /upload/i }));
    const file = new File([new Uint8Array([1, 2, 3])], 'lesson.mp4', { type: 'video/mp4' });
    await userEvent.upload(screen.getByLabelText(/video file/i), file);
    await waitFor(() => expect(screen.getByText(/cdn\/videos\/x\.mp4|uploaded/i)).toBeInTheDocument());
  });
});
```
> Adapt to the real `LessonForm` props/submit mechanism from the existing `LessonForm.test.tsx`. If the form's controls use a `<select>` for source rather than radios, target that. The essential assertions: file select → presign+upload called → `content_json.video_source==='hosted'` + `video_url` set on save.

- [ ] **Step 3: Run — expect FAIL**

Run: `cd invest-ed/frontend && npm test -- LessonForm.video`
Expected: FAIL (no source toggle / upload wiring).

- [ ] **Step 4: Implement the source toggle + upload in `LessonForm.tsx`**

Add state + handlers near the existing video state:
```tsx
import { presignVideo, uploadToPresigned } from '@/api/admin';
// ...
const [videoSource, setVideoSource] = useState<'youtube' | 'hosted'>(
  lesson?.type === 'video' && (cj?.video_source as string) === 'hosted' ? 'hosted' : 'youtube',
);
const [videoUrl, setVideoUrl] = useState(lesson?.type === 'video' ? ((cj?.video_url as string) ?? '') : '');
const [uploadPct, setUploadPct] = useState<number | null>(null);
const [uploadErr, setUploadErr] = useState<string | null>(null);

async function handleVideoFile(file: File) {
  setUploadErr(null);
  if (file.type !== 'video/mp4') { setUploadErr('Please choose an MP4 file.'); return; }
  if (file.size > 200 * 1024 * 1024) { setUploadErr('File too large (max 200 MB).'); return; }
  try {
    setUploadPct(0);
    const res = await presignVideo(file.name, file.type, file.size);
    await uploadToPresigned(res.upload_url, file, setUploadPct);
    setVideoUrl(res.public_url);
    setUploadPct(100);
  } catch (e) {
    setUploadErr(e instanceof Error ? e.message : 'Upload failed');
    setUploadPct(null);
  }
}
```
Update `buildContentJson()` video branch:
```tsx
    if (type === 'video') {
      return videoSource === 'hosted'
        ? { video_source: 'hosted', video_url: videoUrl, caption: videoCaption }
        : { video_source: 'youtube', youtube_id: extractYoutubeId(youtubeInput), caption: videoCaption };
    }
```
In the video JSX block, add a source toggle (radios or a select) and conditionally render the YouTube field or the upload control:
```tsx
{type === 'video' && (
  <div className="space-y-3">
    <fieldset>
      <legend className="mb-1 block text-sm text-ink">Video source</legend>
      <label className="mr-4 text-sm"><input type="radio" name="vsrc" checked={videoSource === 'youtube'} onChange={() => setVideoSource('youtube')} /> YouTube</label>
      <label className="text-sm"><input type="radio" name="vsrc" checked={videoSource === 'hosted'} onChange={() => setVideoSource('hosted')} /> Uploaded video</label>
    </fieldset>

    {videoSource === 'youtube' ? (
      <div>
        <label htmlFor="video-youtube" className="mb-1 block text-sm text-ink">YouTube URL or ID</label>
        <input id="video-youtube" value={youtubeInput} onChange={(e) => setYoutubeInput(e.target.value)}
               className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink"
               placeholder="Paste a YouTube link or 11-character ID." />
      </div>
    ) : (
      <div className="space-y-2">
        <label htmlFor="video-file" className="mb-1 block text-sm text-ink">Video file (MP4, ≤200 MB)</label>
        <input id="video-file" type="file" accept="video/mp4"
               onChange={(e) => { const f = e.target.files?.[0]; if (f) handleVideoFile(f); }} />
        {uploadPct !== null && <p className="text-sm text-muted-foreground">Uploading… {uploadPct}%</p>}
        {videoUrl && <video className="mt-2 w-full max-w-md rounded-md" src={videoUrl} controls playsInline preload="metadata" />}
        {uploadErr && <p className="text-sm text-danger-600">{uploadErr}</p>}
      </div>
    )}

    <div>
      <label htmlFor="video-caption" className="mb-1 block text-sm text-ink">Caption</label>
      <input id="video-caption" value={videoCaption} onChange={(e) => setVideoCaption(e.target.value)}
             className="w-full rounded-md border border-input bg-background px-3 py-2 text-base text-ink" />
    </div>
  </div>
)}
```
> READ the existing video JSX first and replace it in place (keep the surrounding form structure + the existing `extractYoutubeId`). If presign returns 503, `presignVideo` throws → show `uploadErr` "video upload not configured" (map the 503 message). Submitting with `videoSource==='hosted'` and no `videoUrl` should be blocked (disable submit or show an error) — mirror the form's existing required-field handling.

- [ ] **Step 5: Run tests + tsc + lint**

Run: `cd invest-ed/frontend && npm test -- LessonForm && npx tsc -b && npm run lint`
Expected: tests pass (incl. existing LessonForm tests); tsc clean; lint clean (known warnings only).

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/api/admin.ts invest-ed/frontend/src/components/admin/LessonForm.tsx invest-ed/frontend/src/components/admin/__tests__/LessonForm.video.test.tsx
git commit -m "feat(video): admin LessonForm source toggle + R2 upload UI

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Child VideoLesson — hosted `<video>` player

**Files:**
- Modify: `invest-ed/frontend/src/components/child/lesson/VideoLesson.tsx`
- Test: `invest-ed/frontend/tests/unit/child-VideoLesson.test.tsx` (extend)

- [ ] **Step 1: Write the failing test**

In `tests/unit/child-VideoLesson.test.tsx`, add:

```tsx
it('renders an HTML5 <video> for a hosted source', () => {
  const { container } = render(
    <VideoLesson contentJson={{ video_source: 'hosted', video_url: 'https://cdn/videos/x.mp4', caption: 'c' }} onComplete={() => {}} />,
  );
  const video = container.querySelector('video');
  expect(video).not.toBeNull();
  expect(video).toHaveAttribute('src', 'https://cdn/videos/x.mp4');
  expect(video).toHaveAttribute('playsinline');
  // no YouTube iframe in hosted mode
  expect(container.querySelector('iframe')).toBeNull();
});

it('still renders the YouTube iframe when source is youtube (default)', () => {
  const { container } = render(
    <VideoLesson contentJson={{ youtube_id: 'abc123' }} onComplete={() => {}} />,
  );
  expect(container.querySelector('iframe')).not.toBeNull();
});
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd invest-ed/frontend && npm test -- child-VideoLesson`
Expected: FAIL (hosted branch not implemented).

- [ ] **Step 3: Implement the hosted branch**

In `VideoLesson.tsx`, update the `Props.contentJson` type to include `video_source?: 'youtube' | 'hosted'` and `video_url?: string`. At the top of the render, branch:
```tsx
const isHosted = contentJson.video_source === 'hosted' && !!contentJson.video_url;
```
Replace the media block so that when `isHosted`, render:
```tsx
<div className="aspect-video overflow-hidden rounded-md border">
  <video
    src={contentJson.video_url}
    title="Lesson video"
    controls
    playsInline
    preload="metadata"
    className="h-full w-full"
  />
</div>
```
and otherwise keep the existing YouTube `youtubeUrls`/iframe path (only compute `buildYouTubeUrls` in the non-hosted branch). Keep the "Open video on YouTube" link only for the YouTube branch; keep caption/transcript/"I watched this"/Mark-complete for both. The fallback "Video unavailable" still applies when neither a valid `youtube_id` (youtube) nor a `video_url` (hosted) is present.

- [ ] **Step 4: Run tests + tsc**

Run: `cd invest-ed/frontend && npm test -- child-VideoLesson && npx tsc -b`
Expected: all VideoLesson tests pass (old + 2 new); tsc clean.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/lesson/VideoLesson.tsx invest-ed/frontend/tests/unit/child-VideoLesson.test.tsx
git commit -m "feat(video): child hosted <video> player (inline, ad-free)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Extend video-health to hosted URLs

**Files:**
- Modify: `invest-ed/backend/app/services/video_health_service.py`
- Test: `invest-ed/backend/tests/test_video_health_hosted.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_health_hosted.py`:

```python
import httpx
import pytest
from sqlalchemy import select

from app.models.content import Lesson, Level, Module
from app.models.video_health import VideoHealth
from app.services.video_health_service import check_all_videos

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _hosted_lesson(db_session, url):
    m = Module(topic="savings", title="Hosted Mod", country_codes=[], is_premium=False, order_index=0, icon="📈")
    db_session.add(m)
    await db_session.flush()
    lv = Level(module_id=m.id, title="L1", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(lv)
    await db_session.flush()
    lesson = Lesson(module_id=m.id, level_id=lv.id, type="video", order_index=0, xp_reward=15,
                    content_json={"video_source": "hosted", "video_url": url, "caption": "c"})
    db_session.add(lesson)
    await db_session.flush()
    return lesson


async def test_hosted_url_checked_via_http(db_session):
    live = await _hosted_lesson(db_session, "https://cdn/live.mp4")
    dead = await _hosted_lesson(db_session, "https://cdn/dead.mp4")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200 if "live" in str(request.url) else 404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await check_all_videos(db_session, client=client)
    await client.aclose()

    live_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == live.id))
    dead_row = await db_session.scalar(select(VideoHealth).where(VideoHealth.lesson_id == dead.id))
    assert live_row.status == "ok"
    assert dead_row.status == "dead"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_hosted.py -v`
Expected: FAIL (hosted lessons currently mis-handled — blank youtube_id treated as dead, or url not probed).

- [ ] **Step 3: Branch the checker on source**

In `video_health_service.py`, where it currently builds the probe per lesson, determine the source and probe accordingly. Add a helper:
```python
async def _probe_hosted(client, url, sem):
    if not url:
        return "dead", None
    async with sem:
        try:
            resp = await client.get(url, timeout=_TIMEOUT, headers={"Range": "bytes=0-0"})
            sc = resp.status_code
            if sc in (200, 206):
                return "ok", sc
            if sc in (401, 403, 404):
                return "dead", sc
            return "unknown", sc
        except httpx.HTTPError:
            return "unknown", None
```
In `check_all_videos`, for each lesson compute `cj = lesson.content_json or {}`; if `cj.get("video_source") == "hosted"`: probe `_probe_hosted(client, cj.get("video_url",""), sem)` and store the `video_url` as the row's `youtube_id` identifier; else use the existing `_probe(...)` on `cj.get("youtube_id","")`. Keep the rest (upsert, dead_items, stale cleanup) unchanged — `dead_items` for hosted should carry the url in `youtube_id`.

- [ ] **Step 4: Run tests — expect PASS (and existing video-health tests still green)**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_video_health_hosted.py tests/test_video_health_service.py -v`
Expected: pass (the prior YouTube tests remain green).

- [ ] **Step 5: Lint + commit**

```bash
cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app/services/video_health_service.py invest-ed/backend/tests/test_video_health_hosted.py
git commit -m "feat(video): video-health checks hosted URLs too

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Docs (R2 setup) + full regression + push

**Files:**
- Modify: `invest-ed/docs/superpowers/PROGRESS.md`, `invest-ed/AGENTS.md`
- Create: `invest-ed/docs/self-hosted-video-setup.md` (R2 setup guide)

- [ ] **Step 1: Write the R2 setup guide**

Create `invest-ed/docs/self-hosted-video-setup.md`: how to create the R2 bucket; set a public custom/dev domain (`R2_PUBLIC_BASE_URL`); create an S3 API token (access key/secret → `R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`, account id → `R2_ACCOUNT_ID`, bucket → `R2_BUCKET`); set bucket **CORS** to allow `PUT` (+ `Content-Type`) from the app origins (`https://lee-local-code-repo.vercel.app`, `capacitor://localhost`, `http://localhost:5173`); set the five `R2_*` env vars on Railway. Note: until set, admin upload shows "not configured" and YouTube keeps working; files are public-by-URL with unguessable keys.

- [ ] **Step 2: Update PROGRESS + AGENTS**

Add a "Self-hosted video" row to the PROGRESS.md post-launch table (R2 presigned upload + admin source toggle + hosted `<video>` player + video-health coverage; **USER: set up the R2 bucket + `R2_*` env per `docs/self-hosted-video-setup.md`**). Mirror a one-liner in AGENTS.md.

- [ ] **Step 3: Backend regression**

Run: `cd invest-ed/backend && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check . && /Users/leeashmore/Local\ Repo/.venv/bin/pytest`
Expected: ruff clean; tests pass (rely on CI if Postgres hangs).

- [ ] **Step 4: Frontend regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except known warnings; tests pass; build OK.

- [ ] **Step 5: Commit docs + push**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/docs/self-hosted-video-setup.md invest-ed/docs/superpowers/PROGRESS.md invest-ed/AGENTS.md
git commit -m "docs(video): self-hosted video R2 setup guide + progress

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push origin main
```
Confirm all 6 CI jobs green. (Note: `boto3` is a new backend dep — CI's backend job installs `requirements.txt`, so it's covered; the `security` job runs `pip-audit` against it.)

---

## Self-review notes

- **Spec coverage:** R2 client + config-gating (T1), `video_asset` table (T2), presign endpoint + mp4/size validation + hosted-source schema (T3), admin source toggle + direct upload (T4), child hosted `<video>` player (T5), video-health for hosted URLs (T6), R2 setup doc + regression (T7). Both accepted trade-offs (public-by-URL, mp4-only/no-transcode) are enforced (public_url + `only_mp4` validator + size cap) and documented.
- **Placeholder scan:** concrete code + tests throughout; the FE test notes explicitly tell the implementer to adapt to the real `LessonForm` harness (the one judgement area) and the existing video JSX.
- **Type consistency:** `storage.is_configured/create_presigned_put/public_url/delete_object`; `VideoAsset(storage_key,...)`; `VideoPresignRequest/Response` (BE) ↔ `presignVideo`/`uploadToPresigned`/`VideoPresignResponse` (FE); `content_json.video_source`/`video_url` consistent across BE validation, FE form, child player, and the health checker. Migration `e1f2a3b4c5d6` ← `d0e1f2a3b4c5`.
- **Risk notes:** boto3 is mocked in tests (no network/creds). CI doesn't run `alembic upgrade head` (table built via metadata in tests; `create_table` runs on Railway deploy). The presigned-upload + bucket-CORS round-trip can only be fully verified once the user configures R2 — call this out in the close-out (manual verification step).
