# Video Link Health + Admin Visibility — Design

**Status:** Approved (design); pending spec review.
**Date:** 2026-06-05
**Context:** External YouTube videos in the curriculum can be deleted/privated at any time and silently break a lesson (as happened with the Compound Interest video `MqZmwQoHmAA`). This adds automated detection + admin visibility so broken videos surface proactively. Self-hosted curated video is explicitly a **separate, later** sub-project (deferred).

## Goal

Detect dead/unavailable lesson videos automatically and make them easy to see and fix:
1. A **periodic check** (Railway cron) pings each video lesson's YouTube link and emails the admin only when something is broken.
2. An **admin "Video health" page** lists every video lesson with live status + last-checked + a quick edit link + an on-demand "Check now".

Editing a link already exists (admin `LessonForm` accepts a YouTube URL or raw ID and extracts the 11-char id) — this design adds **detection + visibility**, not a new editor.

## Architecture

An async checker pings YouTube's **oEmbed** endpoint per video lesson, classifies the result, and upserts a small `video_health` table. The admin page reads that table (and can trigger a fresh check); a Railway cron command runs the same check on a schedule and emails the admin when videos are dead.

## Data model

New table **`video_health`** (model `app/models/content.py` or a new `app/models/video_health.py`; migration chained from head `c9d0e1f2a3b4`):
- `id` UUID PK
- `lesson_id` UUID FK → `lessons.id`, **unique** (one row per video lesson; cascade delete)
- `youtube_id` String — the id checked (denormalised for display/history)
- `status` String — `"ok"` | `"dead"` | `"unknown"`
- `http_status` Integer | null — the oEmbed HTTP status observed
- `checked_at` DateTime (UTC)

Upserted by lesson_id on every check. Rows for lessons that are no longer video-type or deleted are cleaned up opportunistically (delete rows whose lesson is missing/not video) during a check.

## Checker service (`app/services/video_health_service.py`)

- `async def check_all_videos(session) -> VideoHealthSummary`:
  - Select all `Lesson` where `type == "video"`; read `content_json["youtube_id"]`.
  - For each, GET `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<id>&format=json` via **httpx** (already a dep), per-request timeout (e.g. 8s), small bounded concurrency (e.g. `asyncio.Semaphore(5)`).
  - **Classify:** `200 → "ok"`; `404` or `401 → "dead"` (deleted/private/embedding-forbidden); **timeout / network error / 5xx / 429 → "unknown"** (transient — never treated as dead, never alerted).
  - A missing/blank `youtube_id` on a video lesson → `"dead"` (it can't play).
  - Upsert each result into `video_health` (status, http_status, checked_at). Delete stale rows.
  - Return a summary: counts per status + the list of `dead` items (lesson_id, youtube_id, module/lesson title).
- Pure-ish + injectable HTTP client so tests can mock responses without network. No real network in tests/CI.

## Admin API (in the existing auth-gated admin router, `prefix="/admin"`, `Depends(get_current_admin)`)

- `GET /admin/video-health` → list of `{ lesson_id, module_id, module_title, lesson_title, youtube_id, status, http_status, checked_at | null }` for every video lesson (joined to module/level for context; status from `video_health`, `null`/"unchecked" if never checked).
- `POST /admin/video-health/check` → runs `check_all_videos`, returns the fresh list + summary (so "Check now" updates the page immediately).
- Schemas in `app/schemas/admin.py` (or a new `app/schemas/video_health.py`).

## Cron command (`app/video_health/run.py` → `python -m app.video_health.run`)

- Opens a session, runs `check_all_videos`, and **if `summary.dead` is non-empty**, sends one email to **`settings.admin_alert_email`** (already in config) via the existing sender (`app/services/email.py`; logging backend in dev, Resend in prod) using a new `"video_health_alert"` template listing the dead videos + a pointer to the admin Video health page. No email when nothing is dead.
- Idempotent and safe to run on a schedule. Exits cleanly (no-op email) when `admin_alert_email` is unset or nothing is dead.
- **Scheduling is a USER ops step:** add a Railway cron service/job running `python -m app.video_health.run` on a chosen cadence (e.g. daily). Documented in the spec/README; not auto-created.

## Frontend — admin "Video health" page

- New route under the admin shell + a **sidebar entry** ("🎬 Video health"); light admin theme (matches SP-E), WCAG AA.
- Table/list of video lessons: lesson + module title, `youtube_id`, a **status badge** (`ok` green / `dead` red / `unknown` amber / `unchecked` grey), `checked_at` (relative), an **Edit** link → the existing lesson editor (`/admin/modules/:moduleId/levels/:levelId/lessons` or the lesson form route), and a top-level **"Check now"** button (calls `POST /admin/video-health/check`, shows a spinner, refreshes the list).
- Admin API client methods in `src/api/admin.ts` (or wherever admin API lives).

## Out of scope
- Self-hosting / uploading curated video (storage, player, schema change) — separate later sub-project.
- Auto-replacing dead videos (admin edits the link; no automated substitution).
- Detecting owner-disabled embedding when the video is otherwise public (oEmbed returns 200 → reported "ok"); the dominant failure (deletion/private = 404) is caught. Noted as a known limitation.

## Testing
- **Backend:** checker classifies ok/dead/unknown from mocked httpx responses (200/404/timeout/5xx); blank youtube_id → dead; upsert writes/updates `video_health` + stale-row cleanup; `GET /admin/video-health` lists with status; `POST .../check` updates the table; cron emails `admin_alert_email` **only when** dead (assert via the logging/mock sender) and not otherwise. Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures; **no real network** (inject/patch the HTTP client). Migration head check; local Postgres may hang → rely on CI.
- **Frontend:** Video health page renders the status badges from a mocked list; "Check now" calls the endpoint and refreshes; `vitest-axe` clean; existing admin tests stay green.
- `ruff` + `pytest`; `tsc -b` + lint + test + build; CI 6 jobs green.

## Plan shape
T1 `video_health` model + migration → T2 checker service (httpx classify + upsert + cleanup) + tests → T3 admin endpoints + schemas + tests → T4 cron command + `video_health_alert` email template + tests → T5 FE api + Video health page + sidebar entry + tests → T6 docs (Railway cron setup note) + regression + push.

## Decisions captured
- **Detection via YouTube oEmbed**; classify transient errors as `unknown` (never alert) to avoid false positives. **Railway cron** runs the check + **emails `admin_alert_email` only when dead**. Admin **"Video health" page** + **on-demand "Check now"** in addition to the schedule. New `video_health` table for status history + decoupling the page from live pinging. Self-hosting deferred.
