# Offline support — Phase 3b: auto-sync the active market — design

**Date:** 2026-06-28
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Make a child's **entire active market** available offline **by default**: on app
open (when online), the device pulls a single bulk "offline bundle" of all the
market's content, then on later opens pulls only what changed since last time
(incremental). Storage is trivial (~0.5–1 MB/market; GB today = 450 lessons /
358 kB of JSON), so the win is "offline just works" without the child tapping
anything. Native only; builds on the Phase 3 SQLite content store.

## Context / facts (measured 2026-06-28, prod GB)

- A whole market = **10 modules · 30 levels · 450 lessons · 358 kB** of lesson
  `content_json` (avg 814 B, max ~2 kB). No media in the DB (videos are refs).
  → ~80–100 kB gzipped over the wire; ~0.5–1 MB in SQLite incl. index overhead.
- Lessons currently make **one API call each** (450 for GB) — too many for an
  app-open sync; hence the bulk endpoint.
- `lessons`/`levels`/`modules` have **no `updated_at`/version** column today —
  added here to power the delta.
- Phase 3 already built the native SQLite store (`contentStore.ts` upsert/get +
  `clearForChild`, `sqlite.ts` boundary, `scope.ts`) and the per-level
  `DownloadLevelButton` (which this feature **replaces**).

## Decisions (settled in brainstorming)

- **Trigger:** auto-sync on app open, **any network** (cellular or wifi — it's tiny).
- **Always on, no parent toggle** (negligible footprint; keep it simple).
- **Remove** the per-level `DownloadLevelButton` (auto-sync covers the market).

## Non-goals

- Quiz/practice/review answers, trades, AI — stay online-only (unchanged).
- Web (no SQLite; the existing localStorage persister is unchanged — the sync
  no-ops on web).
- A parent data/storage toggle, wifi-only gating, multi-market pre-download
  (only the **active** market syncs; switching markets re-syncs the new one).
- Tombstone tables — deletions are handled by the `current_ids` reconcile (below).

## Architecture

### Unit 1 — `updated_at` on content (migration)
**Files:** new Alembic migration; `backend/app/models/content.py`.

- Add `updated_at: Mapped[datetime]` to `Module`, `Level`, `Lesson` —
  `server_default=func.now()`, `onupdate=func.now()`, `nullable=False`. Index
  `lessons.updated_at` (the delta query filters on it).
- ORM updates (the admin edit + generation paths use ORM `session` mutations)
  bump `updated_at` automatically via `onupdate`. Backfill existing rows to
  `now()` in the migration (so the first post-deploy bundle returns everything,
  which is correct).

### Unit 2 — the offline-bundle endpoint
**Files:** `backend/app/routers/content.py` (or a small `offline.py`);
`backend/app/services/offline_bundle_service.py`; `backend/app/schemas/`.

- `GET /content/offline-bundle?since=<iso8601|empty>` — auth required; **market
  derived server-side** from the child's active market (`active_market` helper),
  respecting the premium one-market gate (a free child only ever syncs their one
  market — no new gate, just scope to the accessible market).
- Response `OfflineBundleOut`:
  - `market: str`, `server_time: str` (ISO8601 — the client stores this as the
    next `since`; use the DB/server clock, not the client's).
  - `modules: ModuleOut[]` — the full market list (10 items; always returned).
  - `module_levels: dict[str, LevelOut[]]` — keyed by module id (always; small).
  - `level_lessons: dict[str, LessonSummary[]]` — keyed by level id (always; small).
  - `lessons: LessonOut[]` — **only lessons with `updated_at > since`** (or ALL
    when `since` is empty/absent). This is the bulk; everything else is tiny.
  - `current_ids: { modules: str[], levels: str[], lessons: str[] }` — the full
    current id set for the market, for eviction.
- Reuses the existing serialization that `listModules`/`listLevels`/
  `listLevelLessons`/`getLesson` already produce (same `ModuleOut`/`LevelOut`/
  `LessonSummary`/`LessonOut` shapes the SQLite store caches), so the client can
  upsert with the existing `contentStore` fns unchanged.

### Unit 3 — `sync_meta` + client market sync
**Files:** `frontend/src/lib/offline/contentStore.ts` (add `sync_meta` helpers);
`frontend/src/lib/offline/sqlite.ts` (schema v2 — `sync_meta` table);
create `frontend/src/lib/offline/marketSync.ts` + `useOfflineMarketSync.ts`;
`frontend/src/main.tsx` or `Shell.tsx` (mount the hook); `frontend/src/api/content.ts`
(`getOfflineBundle(since)`).

- `sqlite.ts`: schema migration to add
  `sync_meta(child_id TEXT, market TEXT, last_sync TEXT, PRIMARY KEY(child_id, market))`.
- `contentStore.ts`: `getLastSync(scope)` / `setLastSync(scope, iso)`; plus a
  `reconcileIds(scope, {modules, levels, lessons})` that deletes any cached row
  whose id is NOT in the provided current-id sets (handles admin deletes/archives).
- `marketSync.ts`: `syncMarket(scope): Promise<void>` — read `last_sync`, call
  `getOfflineBundle(last_sync)`, then in order: upsert `modules` (→ upsertModules),
  each `module_levels` entry (→ upsertModuleLevels), each `level_lessons` entry
  (→ upsertLevelLessons), each `lessons` item (→ upsertLesson with its level id),
  then `reconcileIds(current_ids)`, then `setLastSync(server_time)`. Wrapped so any
  failure is swallowed (no throw) and leaves the existing cache intact.
- `useOfflineMarketSync()`: on mount (app open), if `isOfflineDbAvailable()` &&
  `onlineManager.isOnline()` && a `scope` exists, fire `syncMarket(scope)` once
  (guarded by a ref so it runs once per app session), in the background. Mount it
  high in the tree (Shell), after `me` is available.

### Unit 4 — remove the manual download button
**Files:** `frontend/src/pages/child/Level.tsx`, delete
`frontend/src/components/child/DownloadLevelButton.tsx` + its test.

- Remove the `DownloadLevelButton` import + mount from `Level.tsx`; delete the
  component + test. The `OfflineBadge` on level cards + the Downloaded view stay
  (they now reflect the auto-synced market). Drop the now-unused i18n keys
  `offline.download` / `offline.saving` if nothing else uses them.

## Data flow

1. App open (native, online) → `useOfflineMarketSync` → `syncMarket(scope)`.
2. First ever sync: `last_sync` empty → bundle returns the **full** market
   (~100 kB gz) → upserted into SQLite → `last_sync = server_time`.
3. Later opens: `since = last_sync` → bundle returns the small metadata + only
   **changed** lessons + the id-set → upsert + reconcile (evict removed) → save
   new `server_time`. Usually near-empty.
4. Offline reads come from SQLite exactly as Phase 3 already serves them
   (cache-first `cacheFirst` wrapper unchanged).
5. Market switch → `clearForChild` already wipes the old scope (Phase 3); the
   next open syncs the new market from `since=null`.

## Error handling / safety

- `syncMarket` is **best-effort**: offline / 5xx / parse error → swallow, log at
  debug, leave the cache + `last_sync` unchanged, retry next open. Never blocks
  the UI (runs in the background).
- **Eviction only on success**: `reconcileIds` runs only when a full, valid
  `current_ids` is present — never on a partial/failed response (so a flaky
  network can't wipe the cache).
- Web / DB-unavailable → `isOfflineDbAvailable()` false → the hook no-ops.
- `server_time` comes from the server clock (avoids client clock skew dropping
  or double-fetching deltas).
- Premium/market scope is server-enforced (a child can only sync their accessible
  market), so the bundle can't leak another market's content.

## Testing

- **Backend:** `since` empty → full set (all lessons + correct `current_ids`);
  `since=T` → only lessons with `updated_at > T`; market-scoped (no other
  market's rows); premium-gated (free child → their one market only);
  `updated_at` bumps on an ORM lesson edit; `server_time` present + ISO8601.
- **Client (mocked store + bundle):** first sync (since null) upserts all four
  shapes + sets `last_sync`; second sync sends the stored `since` + applies only
  deltas; `reconcileIds` deletes cached ids absent from `current_ids` and keeps
  present ones; eviction does NOT run on a failed/partial fetch; hook no-ops on
  web / offline / no-scope; runs once per session.
- **Removal:** `Level.tsx` no longer renders the download button; the deleted
  component's test is removed; suite stays green (baseline unchanged).

## Implementation phasing (single plan)

1. Migration: `updated_at` on modules/levels/lessons (+ index + backfill) + ORM `onupdate`.
2. `offline_bundle_service` + `OfflineBundleOut` schema + `GET /content/offline-bundle` + tests.
3. SQLite schema v2 (`sync_meta`) + `contentStore` `getLastSync`/`setLastSync`/`reconcileIds` + tests.
4. `getOfflineBundle` client fn + `marketSync.syncMarket` + tests.
5. `useOfflineMarketSync` hook + mount in Shell + test.
6. Remove `DownloadLevelButton` + mount + test; drop unused i18n keys.
7. Verify (ruff + pytest; tsc + lint + vitest + build) → ship (CI → Railway has a
   DB migration: **ask about a prod snapshot first** → Vercel → cap sync) → docs.

## Future (out of scope)

- Multi-market pre-download / a "download other markets" affordance.
- A parent data/storage toggle or wifi-only gating (revisit only if footprint grows).
- Background/periodic sync beyond app-open.
