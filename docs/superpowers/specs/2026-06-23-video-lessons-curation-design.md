# Video Lessons Curation — Design Spec

**Date:** 2026-06-23
**Status:** Approved (design); implementation plan to follow.

## Goal

Bring curated YouTube video lessons back into the curriculum, and stop them
disappearing again. One admin **video-curation** surface reviews *candidate*
videos and approves each into a `video` lesson, fed by two sources: **recovered**
(the operator's old hand-picked videos, salvaged from archived modules before they
are purged) and **suggested** (on-demand YouTube-API results for a concept).

## Background / problem

`video` lessons (`Lesson.type == "video"`, content holds a `youtube_id`) were
**hand-curated**; the AI content generator only produces `card`/`quiz`/`scenario`
and explicitly skips `video` (`admin_content_generation_service.py` — `video` not in
`_SCHEMA_HINT`). When GB/US/HK were regenerated and republished, the old modules
holding the curated videos were **auto-archived**, and archived modules are
**hard-purged 30 days after archival** (`archived_module_retention_days = 30`,
`module_purge_service.py`). Archived 2026-06-22 → permanently deleted ≈2026-07-22.
So the curated picks are recoverable but on a clock, and new content has no videos.

## Architecture

One review-queue table (`VideoCandidate`) + one admin curation page. Both sources
write candidates into the queue; the operator approves a candidate → a `video`
lesson is created in a chosen level. Every candidate must pass the existing
video-health embeddability/age-restriction check before approval, so nothing
broken or unsafe reaches a child. Safety for the *lesson content* is unchanged
(it's a known-safe embeddable YouTube video, operator-approved).

**Tech stack:** FastAPI + SQLAlchemy 2.0 async + Alembic (backend), React 18 +
Vite + TanStack Query + Tailwind (admin frontend), YouTube Data API v3 (existing
`youtube_api_key`), existing `video_health_service` for embeddability checks.

## Global constraints

- Kids' app: WCAG 2.2 AA on new admin UI (`vitest-axe`); only embeddable,
  non-age-restricted, reachable videos may be approved.
- DB change = hand-written, chained Alembic migration (`alembic heads` first);
  **ask before applying the prod migration whether to snapshot**.
- Admin-only endpoints (reuse `get_current_user` + `is_admin`); follow existing
  admin router/UI patterns. Cron-gated `/internal/*` jobs need a CSRF allowlist entry.
- Beta: commit straight to `main` on green CI.

## Data model — `VideoCandidate` (new table)

A review queue, shared by both sources.

| field | type | purpose |
|---|---|---|
| `id` | uuid PK | |
| `youtube_id` | str | the video |
| `title` | str | display |
| `thumbnail_url` | str \| null | preview |
| `source` | enum `recovered` \| `suggested` | provenance |
| `market_code` | str FK→markets | which market |
| `origin_context` | str \| null | old module/topic (recovered) or concept searched (suggested) |
| `suggested_module_id` | uuid FK→modules, null | topic-matched home in the *current* curriculum |
| `suggested_level_id` | uuid FK→levels, null | matched level (operator can change) |
| `embeddable` | bool \| null | video-health result (null until checked) |
| `health_detail` | str \| null | why blocked (age-restricted / embedding disabled / dead) |
| `status` | enum `pending` \| `approved` \| `skipped` | review state |
| `created_lesson_id` | uuid FK→lessons, null | the `video` lesson it became |
| `created_at` | datetime | |

Unique constraint `(youtube_id, market_code)` so re-running extraction/suggestion
never duplicates. One Alembic migration creates the table + enums + FKs.

## Sub-project A — Salvage (build first; time-sensitive)

1. **Durable extraction (defuses the purge).** A one-off, **idempotent** cron-gated
   internal endpoint (`POST /internal/video-candidates/extract`, same pattern/CSRF
   exemption as other `/internal/*` jobs) scans **archived** modules
   (`archived_at IS NOT NULL`) for `type="video"` lessons. For each it inserts a
   `VideoCandidate`: `source=recovered`, `market_code` + `origin_context` from the
   old module, `suggested_module_id/level_id` set by **topic-match** — the old
   module's `topic` → the current published (non-archived) module with the same
   `topic` + `market_code` (first level by default). Dedup on `(youtube_id,
   market_code)`. Logs found/created counts. Once this runs, the picks survive the
   purge.
2. **Health backfill.** On extraction (or lazily on first view) run the existing
   video-health check per candidate → set `embeddable`/`health_detail`.
3. **Admin curation page** (new "Video Curation" sidebar item, market-filter like
   the Modules page): lists `pending` candidates grouped by market → module, each
   with an embedded YouTube preview, a `recovered`/`suggested` badge, the suggested
   module+level as editable dropdowns, the health status, and **Approve** / **Skip**.
4. **Approve → lesson** (`POST /admin/video-candidates/{id}/approve` with chosen
   module/level): blocked unless `embeddable`; creates a `video` lesson
   (`content={youtube_id, video_source:"youtube"}`) appended to the level via the
   existing lesson-create path; sets candidate `approved` + `created_lesson_id`.
   **Skip** (`.../skip`) sets `skipped`.

## Sub-project B — Forward suggestion (after A; reuses A's queue + approve flow)

- **"Suggest videos"** action on a module/level →
  `POST /admin/video-candidates/suggest {module_id|level_id}`: build a search query
  from the concept title + market, call YouTube Data API `search.list`
  (`safeSearch=strict`), then `videos.list` to keep only **embeddable +
  not-age-restricted** (reuse video-health logic), and insert the survivors as
  `source=suggested` candidates (with `suggested_module_id/level_id` = the
  requesting module/level). They appear in the same review queue for approve/skip.
- Operator-paced, so YouTube quota (search.list = 100 units/call, ~100/day default)
  is a non-issue. API errors/quota degrade gracefully (message, no crash).

## Error handling

- Approval gated on `embeddable=True`; a failed/blocked health check shows the
  reason and disables Approve.
- Extraction & suggestion are idempotent (unique constraint) and log counts.
- YouTube API failure → surfaced as an admin message; never 500s the page.
- Topic-match miss (no current module with that topic) → candidate still created
  with `suggested_module_id=null`; operator picks the home manually.

## Testing

- **Backend:** extraction idempotency + topic-match (incl. null-match); approve
  creates the `video` lesson in the right level + links candidate; approve blocked
  when not embeddable; skip transitions; suggestion endpoint with **mocked**
  YouTube (filters non-embeddable/age-restricted); migration up/down.
- **Frontend:** curation page renders the queue grouped by market/module; approve
  / skip / re-place actions call the right endpoints; **vitest-axe** on the page.

## Phasing & risk

- **A first** — its task 1 (extraction) is the only deadline item (≈2026-07-22
  purge); ship it early even before the full UI so nothing is lost. Then the
  curation UI + approve flow.
- **B after** — small addition (one suggestion endpoint + a button) on A's surface.
- **Risk:** if extraction isn't run before the purge, the recovered videos are gone.
  Mitigation: extraction is the first implemented + run task; optionally bump
  `archived_module_retention_days` as a temporary backstop until it runs.
