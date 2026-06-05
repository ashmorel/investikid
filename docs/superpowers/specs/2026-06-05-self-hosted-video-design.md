# Self-Hosted Curated Video (Cloudflare R2) — Design

**Status:** Approved (design); pending spec review.
**Date:** 2026-06-05
**Context:** Lesson videos today are YouTube embeds, which carry ads, "video unavailable" breakage, and iOS WKWebView quirks (the error-153 saga). This adds an optional **self-hosted** video source per lesson: admins upload a curated MP4 to our own Cloudflare R2 bucket; children play it inline from R2's CDN — ad-free, no third-party tracking, no 153. YouTube remains a per-lesson alternative (this **augments**, not replaces).

## Goal

Let admins host curated lesson videos under our control and have children play them inline in web + iOS, without changing the existing YouTube-based lessons.

## Decisions (locked via brainstorming)
- **Augment**, not replace: a video lesson is EITHER `youtube` or `hosted`.
- **Cloudflare R2** object storage (S3-compatible, zero egress). **In-app admin upload** via presigned PUT (browser → R2 directly; file never transits the API).
- **Access:** R2 objects are **public-read with unguessable random keys** (`videos/{uuid}.mp4`) — same posture as the public YouTube embeds. Premium-module hosted files are therefore reachable by anyone holding the URL (not signed). Accepted trade-off for parity; signed URLs are a future hardening.
- **Format:** **MP4 (H.264/AAC) only, no server-side transcoding.** Enforce `content_type == video/mp4` + a size cap (200 MB). Admins upload a web-ready file.
- **Feature-gated:** when `R2_*` env is unset, upload endpoints return `503 not_configured` and the admin UI shows "video upload not configured"; the YouTube path is unaffected (mirrors the SP-D1 OAuth not-configured pattern).

## Architecture

Admin uploads in the admin `LessonForm`: the browser asks the backend for a short-lived **presigned PUT URL** (boto3 against the R2 S3 endpoint), uploads the file **directly to R2**, then the lesson's `content_json` stores `video_source: "hosted"` + the file's public CDN `video_url`. Children's `VideoLesson` renders an HTML5 `<video playsinline>` from that URL. A `video_asset` table tracks uploaded files for management + health checks.

## Components

1. **R2 storage service** — `app/services/storage.py`:
   - boto3 S3 client built from env: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE_URL` (the public bucket/CDN domain). Endpoint = `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`.
   - `is_configured() -> bool`; `create_presigned_put(key, content_type, expires=900) -> str`; `public_url(key) -> str` (`{R2_PUBLIC_BASE_URL}/{key}`); `head_object(url|key) -> bool` (for health); `delete_object(key)`.
   - All R2 config in `app/core/config.py`; documented in `.env.example`.
2. **`video_asset` table** — model `app/models/video_asset.py` + Alembic migration chained from head `d0e1f2a3b4c5`:
   - `id` UUID PK, `storage_key` String unique, `content_type` String, `size_bytes` Integer|null, `original_filename` String|null, `created_at` DateTime(tz).
3. **Admin presign endpoint** (admin router, `Depends(get_current_admin)`):
   - `POST /admin/video-assets/presign` — body `{ filename, content_type, size_bytes }`. Validates `content_type == "video/mp4"` and `size_bytes <= 200*1024*1024`; if `not storage.is_configured()` → `503 {"detail":"not_configured"}`. Generates `key = f"videos/{uuid4()}.mp4"`, inserts a `video_asset` row, returns `{ asset_id, key, upload_url, public_url }`.
   - (No separate confirm step — the lesson save records the `video_url`; a stray asset whose lesson is never saved is an orphan tolerated for a curated library and visible via the video-health page.)
4. **Lesson schema** — video `content_json` gains `video_source: "youtube" | "hosted"` (absent/legacy ⇒ treated as `"youtube"` for back-compat). Hosted also carries `video_url` (+ optional `video_asset_id`). `app/schemas/admin.py` video validation: `source=="hosted"` requires a non-empty `video_url`; `source=="youtube"` requires `youtube_id` (current rule). The child content responses already pass `content_json` through.
5. **Admin `LessonForm.tsx`** (video type): a **source toggle** (YouTube / Uploaded video). YouTube → the existing "YouTube URL or ID" field. Uploaded → a file `<input type="file" accept="video/mp4">` → on select: client-side validate type/size → `POST /admin/video-assets/presign` → `PUT` the file to `upload_url` (XHR with upload-progress) → on success set `content_json.video_source="hosted"`, `video_url=public_url`, `video_asset_id`. Show progress + a small `<video>` preview. Submits the lesson as today. Shows "video upload not configured" when presign returns 503.
6. **Child `VideoLesson.tsx`**: branch on `content_json.video_source` (default youtube). `hosted` → `<video controls playsinline preload="metadata" src={video_url}>` (full-bleed, rounded, same container as the iframe) + keep caption/transcript/"I watched this"/Mark-complete. `youtube` → unchanged (the existing nocookie/proxy path). `videoEmbed.ts` is unchanged (only used for the youtube branch).
7. **Video-health integration**: extend `video_health_service.check_all_videos` to also cover hosted lessons — for `video_source=="hosted"`, do an HTTP `HEAD`/ranged `GET` on `video_url` (200/206 → ok, 403/404 → dead, transient → unknown). Hosted broken files then surface in the admin "Video health" page + the cron alert alongside YouTube ones. The `video_health` row's `youtube_id` column is reused to store the asset key/url for hosted rows (or add a nullable `kind` column — implementer's call; keep it minimal).

## COPPA / safety
Self-hosted curated video is **safer** than YouTube: no ads, no related-video rabbit holes, no third-party tracking/cookies, content fully under editorial control. No PII is stored in R2 (only curated lesson media). The public-by-URL access is no weaker than the current public YouTube embeds.

## Out of scope (future)
- Signed/expiring playback URLs for premium protection; server-side transcoding / adaptive HLS; in-app video trimming; auto-captions; bulk migration of existing YouTube lessons to hosted; managed-platform (Mux/Stream) delivery.

## Testing
- **Backend:** storage service `is_configured`/`create_presigned_put`/`public_url`/`delete_object`/`head_object` with **boto3 mocked** (no network/credentials); presign endpoint — admin-only (401/403), 503 when unconfigured, rejects non-mp4 + oversized, returns the envelope + creates a `video_asset` row; schema validation (hosted requires `video_url`, youtube requires `youtube_id`); `video_asset` model roundtrip; health checker handles hosted URLs via a mocked HTTP client. Async tests use `pytestmark loop_scope="session"` + `client`/`admin_client`/`db_session`; **no real network/R2**. Migration head check; local Postgres may hang → rely on CI.
- **Frontend:** `LessonForm` source toggle renders both branches; the upload flow (mock presign + mock PUT) sets `video_url` and previews; 503 → "not configured" message. `VideoLesson` renders `<video>` with the hosted URL for `source=hosted` and the YouTube path for `source=youtube`; `vitest-axe` clean; existing lesson/video tests stay green.
- `ruff` + `pytest`; `tsc -b` + lint + test + build; CI 6 jobs green.

## User setup (one-time, documented in `.env.example` + a setup note)
Create an R2 bucket + a **public** custom/dev domain (`R2_PUBLIC_BASE_URL`); create an API token (S3 access key/secret); set the bucket **CORS** to allow `PUT` from the app origins (Vercel web + `capacitor://localhost` + localhost dev); set the five `R2_*` backend env vars on Railway. Until set, upload returns `503 not_configured` and YouTube keeps working.

## Plan shape
T1 R2 config + `storage.py` service (+tests) → T2 `video_asset` model + migration → T3 presign endpoint + admin schema validation (+tests) → T4 admin `LessonForm` source toggle + upload UI (+tests) → T5 child `VideoLesson` hosted `<video>` player (+tests) → T6 extend video-health to HEAD hosted URLs (+tests) → T7 docs (R2 setup) + full regression + push.

## Decisions captured
Augment (per-lesson `video_source` youtube|hosted; legacy⇒youtube) · **Cloudflare R2** + boto3 presigned PUT (browser→R2 direct) · public-read unguessable keys (premium files public-by-URL — accepted) · **MP4-only, no transcode**, `video/mp4` + 200 MB cap · feature-gated `503 not_configured` when `R2_*` unset · HTML5 `<video playsinline>` player (ad-free, inline on iOS) · video-health extended to hosted URLs · signing/transcoding/HLS deferred.
