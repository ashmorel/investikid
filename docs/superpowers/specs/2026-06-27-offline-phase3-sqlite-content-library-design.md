# Offline support — Phase 3: structured SQLite content library — design

**Date:** 2026-06-27
**Status:** Approved (design) — pending spec review → implementation plan

## Goal

Move the offline cache for **learning content** (modules, levels, lessons) off
the ~5MB single-blob localStorage persister and into a **structured, native
SQLite store** that is queryable per-entity — and surface it to the child as a
browsable **offline library** ("available offline" badges + a downloaded view +
an explicit "download this level for offline" action). Native only (iOS +
Android); web keeps the shipped localStorage persister untouched.

## Context

- Phase 1 wired `@capacitor/network` → TanStack `onlineManager` and persisted an
  allowlist of query keys to localStorage as a single serialized blob.
- Phase 2a added a PWA app-shell precache + lesson prefetch (`usePrefetchLevelLessons`
  writes `['lesson', id]` into the persisted cache).
- Phase 2b added the lesson-completion sync outbox on TanStack's paused/persisted
  mutations. **This stays exactly as-is** — Phase 3 does not touch it.
- The persister stores the **whole** dehydrated cache as one blob (all-or-nothing
  rehydrate), capped ~5MB by localStorage, written synchronously on the main
  thread. Lesson bodies are the bulk of cacheable data and the cap pressure.

### Grounding facts that constrain the design

- Content payloads **mix immutable content** (`title`, `body`, `xp_reward`,
  `order_index`) **with per-child mutable state** (`completed`, `locked`,
  `lessons_completed`, `passed`, `mastered_at`).
- `module-levels` and `level-lessons` are **market-scoped** — `RegionSwitcher`
  invalidates `['modules']`, `['module-levels']`, `['level-lessons']` on region
  change. The SQLite cache must therefore be **scoped by `(child_id, market)`**.
- Content carries **no server `version`/`updated_at`** field. Staleness is
  `cached_at` + a max age, with **overwrite on every successful online fetch**.
- Offline-rendered `completed`/progress flags may be **slightly stale** — this is
  already true of Phase 1 persistence and is acceptable. The online path (2b
  outbox + invalidation) reconciles authoritative state.
- Web has no SQLite; we deliberately do **not** add `jeep-sqlite`. On web (and on
  any native device where the DB can't open), all offline-store calls no-op and
  callers fall back to the existing network/RQ behavior.

## Non-goals

- Quiz/practice/review answer caching, trades offline — unchanged (LLM/live-price
  dependent; online-only).
- Touching the Phase 2b completion outbox, the web persister, or Phase 1/2a
  semantics on web.
- Encryption at rest — cached content is public learning material, no PII.
- A background/periodic sync service. "Download for offline" is an explicit,
  foreground, user-initiated bulk-ingest; ordinary viewing writes through
  opportunistically.
- Caching admin/parent/coach/news/search queries (never in scope).

## Architecture (native-only SQLite content cache; persister + outbox unchanged)

### Unit 1 — DB connection + migrations
**File:** create `frontend/src/lib/offline/sqlite.ts`.

- `isOfflineDbAvailable(): boolean` — `Capacitor.isNativePlatform()` AND the
  `@capacitor-community/sqlite` plugin is registered. Memoized.
- `getDb(): Promise<SQLiteDBConnection | null>` — lazily open/create the
  `investikid` DB, run **forward-only versioned migrations** (the plugin's
  `addUpgradeStatement` / `upgrade` set), return a shared connection. Returns
  `null` (never throws) when unavailable or on open failure → callers fall back.
- Schema version constant lives here; every schema change adds an upgrade
  statement and bumps the version.

### Unit 2 — Content store DAL
**File:** create `frontend/src/lib/offline/contentStore.ts`.

Tables (all scoped by `child_id` + `market`, payload stored as JSON text):

```
cached_modules(child_id TEXT, market TEXT, payload_json TEXT, cached_at INTEGER,
               PRIMARY KEY(child_id, market))
cached_module_levels(child_id, market, module_id TEXT, payload_json, cached_at,
               PRIMARY KEY(child_id, market, module_id))
cached_level_lessons(child_id, market, level_id TEXT, payload_json, cached_at,
               PRIMARY KEY(child_id, market, level_id))
cached_lesson(child_id, market, lesson_id TEXT, level_id TEXT, payload_json,
               cached_at, PRIMARY KEY(child_id, market, lesson_id))
```

Methods (all async, all try/catch → return `null`/`[]`/`false` on failure, never
throw; all no-op when `!isOfflineDbAvailable()`):

- `upsertModules(payload)` / `getModules(): Promise<ModuleOut[] | null>`
- `upsertModuleLevels(moduleId, payload)` / `getModuleLevels(moduleId)`
- `upsertLevelLessons(levelId, payload)` / `getLevelLessons(levelId)`
- `upsertLesson(lesson)` / `getLesson(lessonId)` — `level_id` denormalized so a
  lesson can be associated with its level for the availability view.
- `listAvailableOffline(): Promise<OfflineAvailability>` — which levels have all
  their lessons cached (drives badges + the downloaded view).
- `clearForChild()` — wipe all rows for the active `(child_id, market)`; called
  on logout and on region change (mirrors the RQ invalidation).

`(child_id, market)` come from the active session/market context already in the
app (the same source `RegionSwitcher` uses). A row older than `OFFLINE_MAX_AGE`
(24h, matching `PERSIST_MAX_AGE`) is treated as a miss for *fallback* reads but
is still overwritten on the next online fetch.

### Unit 3 — Query wiring (cache-first with write-through)
**Files:** create `frontend/src/lib/offline/useOfflineContent.ts`; modify the
content query call sites + `usePrefetchLevelLessons`.

- A helper that wraps a content `queryFn`: attempt the network call → on success
  `upsert` into the store and return → on a **network/offline** failure, read the
  store and return the cached payload if present (else rethrow so the existing
  offline UI shows). `placeholderData`/`initialData` seeded from the store for
  instant first paint.
- `usePrefetchLevelLessons` (2a) writes through the same `upsertLesson`, so an
  online level visit populates SQLite.
- Applies to `['modules']`, `['module-levels', id]`, `['level-lessons', id]`,
  `['lesson', id]`.

### Unit 4 — Native persist-allowlist trim
**Files:** modify `frontend/src/lib/queryPersistence.ts`, `frontend/src/main.tsx`.

- On native (SQLite owns content), exclude the content heads (`modules`,
  `module-levels`, `level-lessons`, `lesson`, `module`) from the localStorage
  persist blob → relieves the 5MB pressure. On web, the allowlist is unchanged.
- One guarded branch (a `contentKeysPersisted` flag derived from
  `isOfflineDbAvailable()`); `shouldDehydrateQuery` consults it.

### Unit 5 — Native plugin config
**Files:** `frontend/package.json`, `frontend/capacitor.config.ts`, iOS/Android
native projects via `cap sync`.

- Add `@capacitor-community/sqlite`. No encryption. DB opened lazily inside the
  existing async bootstrap. iOS/Android pick up the plugin via `cap sync`
  (Podfile/Gradle handled by Capacitor). **Native rebuild (Xcode/Gradle) is an
  operator follow-up** to ship the plugin on device — same pattern as Phase 1's
  `@capacitor/network`.

### Unit 6 — Availability UX (Figma-first)
**Files:** new badge component + a downloaded-content view + a "download this
level for offline" action; mounts on the Learn/Level surfaces.

- **"Available offline" badge** on levels/lessons whose content is fully cached
  (reads `listAvailableOffline()`).
- **Downloaded view** — a simple list of what's saved for offline, with the
  option to remove.
- **"Download this level for offline" action** — explicit foreground bulk-ingest:
  fetch every lesson in the level while online and `upsert` them, with progress
  feedback; disabled/hidden offline.

**Per the standing Figma-first rule, these surfaces are mocked up in Figma and
approved before implementation.** Badges are near-trivial; the downloaded view +
download action are new surfaces → full mockups.

## Data flow

1. Online lesson view → `queryFn` fetches → `upsertLesson` → renders.
2. Later offline → same key → network fails → `getLesson` returns the cached
   payload → renders (possibly-stale `completed`, as today).
3. "Download this level" (online) → bulk `upsertLesson` for every lesson → the
   level shows "available offline".
4. Region switch / logout → `clearForChild()` wipes the scoped rows (mirrors the
   RQ invalidation), so a different market/child never sees another's cache.

## Error handling / safety

- DB unavailable / open failure / plugin absent → `isOfflineDbAvailable()` false
  → every call no-ops → app behaves exactly as pre-Phase-3 (never blocks render).
- Every DAL method is try/catch → returns null/empty on failure; a corrupt row
  can't break a screen.
- Schema migrations are forward-only and versioned.
- Scoping by `(child_id, market)` + `clearForChild()` on logout/region-change
  prevents cross-child / cross-market leakage.

## Testing

- **DAL** (mocked `@capacitor-community/sqlite`): upsert→get round-trips; scoping
  by child + market; overwrite-on-reupsert; staleness past `OFFLINE_MAX_AGE`;
  `clearForChild` wipes only the active scope; `listAvailableOffline` correctness;
  every method no-ops (returns null/false) when `isOfflineDbAvailable()` is false.
- **Query wiring**: online success upserts + returns; offline failure reads from
  store; web/unavailable falls back to network (no store calls); prefetch writes
  through.
- **Persist trim**: on native, content heads excluded from `shouldDehydrateQuery`;
  on web, unchanged (existing `queryPersistence` tests stay green).
- **Availability UX**: badge shows only when fully cached; download action
  bulk-ingests + reflects progress; disabled offline. (`vitest-axe` on new UI.)
- No new e2e. Native-on-device verification is operator QA after the native build.

## Implementation phasing (single plan, ordered)

1. `sqlite.ts` — connection + migrations + `isOfflineDbAvailable` (+ tests).
2. `contentStore.ts` — DAL tables + methods (+ tests, mocked plugin).
3. `useOfflineContent.ts` — cache-first write-through wiring; wire the 4 content
   queries + prefetch (+ tests).
4. Native persist-allowlist trim (+ tests).
5. Plugin install + `capacitor.config` + `cap sync`.
6. Figma mockups for the availability UX → approve.
7. Availability UX implementation (badge + downloaded view + download action,
   `vitest-axe`).
8. Full verify (tsc + lint + vitest + build) → push → green CI → Vercel → docs.
   Native rebuild flagged as operator follow-up.

## Future (out of scope)

- Background/periodic content refresh.
- Extending the structured store to a durable outbox table (the Phase 2b outbox
  stays on TanStack unless a concrete robustness problem emerges).
- Web SQLite via `jeep-sqlite` (only if a web offline-library need arises).
