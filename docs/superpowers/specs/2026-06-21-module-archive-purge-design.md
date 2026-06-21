# Module Archive + 30-Day Purge — Design

**Date:** 2026-06-21
**Status:** Approved (brainstorm)
**Branch/flow:** `main` (beta straight-to-main)

## Problem
The admin **Modules** tab lists every module, including ones retired from the live
curriculum (e.g. the 15 original GB modules left `published=false` after a republish).
They're no longer shown in the app but clutter the admin and confuse the operator.

## Goal
- Move retired/old modules out of the main list into a separate **Archived** section.
- "Delete" becomes a **soft-archive** (recoverable), not a hard delete.
- Archived modules are **permanently purged after 30 days**.
- Restorable before purge.

## Decisions (locked)
1. **Archived = auto + manual + backfill.** Explicitly-deleted modules AND modules
   auto-retired by a curriculum republish go to Archived; a one-time migration backfill
   moves today's genuinely-retired modules there.
2. **Deleting a LIVE module is blocked** (must unpublish/replace first).
3. **Restore** is supported before the 30-day purge.

## Data model
Add one nullable column to `modules`:
- `archived_at: timestamptz NULL` — `NULL` = active (live or staged, shown in the main
  list); set = archived (shown in Archived; the 30-day clock runs from this value).
- Index `archived_at` (the purge query filters on it).
- Retention is config: `settings.archived_module_retention_days: int = 30`
  (mirrors the existing `data_retention_days` pattern in `app/core/config.py`).

Child data is untouched. Archived modules are `published=false`, which the kid-facing
feeders (`content_service.is_module_visible` / `get_accessible_module`) already hide —
so nothing changes in the app.

## Migration
New Alembic revision (down_revision = current head `c3e5a7b9d1f2`):
1. `add_column modules.archived_at timestamptz NULL` + index.
2. **Backfill** — archive genuinely-retired modules only:
   `UPDATE modules SET archived_at = now() WHERE published = false AND NOT EXISTS (`
   `  SELECT 1 FROM market_curriculum_proposal p,`
   `       jsonb_array_elements((p.proposal_json)::jsonb->'modules') m`
   `  WHERE p.status IN ('proposed','accepted','published')`
   `    AND (m->>'module_id')::uuid = modules.id)`.
   This archives retired-old modules (not referenced by any active proposal — e.g. the
   pre-engine GB seed modules) while leaving **staged in-progress** modules
   (which *are* in an accepted proposal) active.
3. Downgrade: drop index + column.

## Backend
`app/models/content.py` — add `archived_at` to `Module`.

`app/schemas/admin.py` — add `archived_at: datetime | None` to `AdminModule`/`ModuleOut`;
construct it from `module.archived_at` everywhere those are built.

`app/routers/admin.py`:
- `DELETE /modules/{id}` (`delete_module`) → **soft-archive**:
  - 404 if missing.
  - **409 if `module.published is True`** ("Unpublish or replace this live module before archiving").
  - else `module.archived_at = now()`, commit, return the module. (No hard delete here.)
- New `POST /modules/{id}/restore` → 404 if missing; if `archived_at` is set, clear it
  (back to the main list, clock reset); commit, return the module.

`app/services/market_curriculum/curriculum_publish_service.py` — in
`publish_market_curriculum`, the same `UPDATE` that retires the previously-live modules
(`published=False`) also sets `archived_at = now()` so they auto-move to Archived.

## Purge cron
`app/routers/internal.py` — new `POST /internal/purge-archived-modules`, X-Cron-Secret
gated (reuse the existing header check pattern). Hard-deletes modules where
`archived_at < now() - retention`; deletes child `Lesson` rows first then the modules
(mirrors current `delete_module`); DB `ON DELETE CASCADE` cleans up levels/lessons/
progress/drafts. Returns `{"purged": n}`.

`app/core/csrf.py` — add `/internal/purge-archived-modules` to `_DEFAULT_EXEMPT_PATHS`
(unauth POST must return 401/503, not 403 — verify with an unauth curl).

`.github/workflows/video-health-cron.yml` — add a step that POSTs the new endpoint with
`X-Cron-Secret: $CRON_SECRET` (independent step, `--retry` for cold starts, like the
existing jobs). No new workflow file.

## Frontend (`frontend/src/components/admin/ModuleList.tsx`)
- `useModules()` already returns all modules. Split:
  - **Main list** = `archived_at == null` (current reorder/edit/delete behaviour).
  - **Archived** = `archived_at != null`, rendered in a collapsible section below, each
    row showing **"Auto-deletes in N days"** (from `archived_at + 30d`) and a **Restore**
    button. No reorder in Archived.
- "Delete" confirm copy → "Archive this module? It moves to Archived and is permanently
  deleted after 30 days — you can restore it before then." Live modules: Delete disabled
  (or the 409 message surfaced).
- `frontend/src/api/admin.ts` — add `archived_at: string | null` to `AdminModule`; add
  `useRestoreModule` (POST `/admin/modules/{id}/restore`, invalidates `['admin','modules']`).

## Testing
Backend:
- archive sets `archived_at`; archiving a **published** module → 409.
- restore clears `archived_at`.
- `publish_market_curriculum` sets `archived_at` on retired modules.
- purge deletes only `archived_at < cutoff`, leaves recent archives + active modules, and
  cascade-removes child rows.
- purge endpoint cron-secret gate (401 without/with wrong secret) + CSRF exemption
  (unauth POST → 401/503, not 403).
- migration backfill archives a retired module but not a staged (in-proposal) one.

Frontend (`ModuleList.test.tsx`):
- archived modules render in the Archived section, not the main list; countdown shown;
  Restore calls the hook; live-module delete is blocked.

## Out of scope
Bulk archive/restore; per-module custom retention; archiving levels/lessons individually.
