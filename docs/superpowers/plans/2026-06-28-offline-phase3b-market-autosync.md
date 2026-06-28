# Offline Phase 3b — Auto-Sync the Active Market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A child's entire active market is cached for offline by default — on app open the device pulls a single bulk "offline bundle" (full first time, only-changed-since after), into the existing Phase 3 SQLite store; the manual per-level download button is removed.

**Architecture:** A new `updated_at` column on modules/levels/lessons powers an incremental `GET /content/offline-bundle?since=` endpoint that returns the market's content (metadata in full, lessons as a delta) plus a current-id set for eviction. A client hook calls it once per app open, upserts deltas into SQLite via the existing `contentStore` fns, and evicts ids no longer present.

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · React 18 · TanStack Query 5 · Capacitor 8 (`@capacitor-community/sqlite`) · vitest · pytest.

## Global Constraints

- **Native-only client behaviour.** The sync + store are gated on `isOfflineDbAvailable()` (= `isNativeApp()`); on web everything no-ops (web keeps the localStorage persister). Do NOT touch web behaviour.
- **Reuse, don't duplicate.** The bundle MUST return the exact `ModuleOut`/`LevelOut`/`LessonSummary`/`LessonOut` shapes the per-item content routes already return (the SQLite store caches those shapes). Extract the routes' serialization into reusable helpers and call them from both — no parallel serializers.
- **Market + premium scope is server-enforced.** The bundle's market = the child's active market (`active_market(user)`); a free child only ever syncs their one accessible market — never another market's content.
- **Best-effort sync, eviction-only-on-success.** `syncMarket` swallows all errors (offline/5xx/parse) and leaves the cache + `last_sync` untouched; `reconcileIds` (eviction) runs ONLY on a complete valid `current_ids` — never on a partial/failed fetch.
- **`server_time` is the server clock** (from the DB / response), stored by the client as the next `since` — never the client clock.
- **No `as any`** (CI: `npm run lint` = `eslint .`, error-level). Backend: `ruff check .` clean over the whole dir.
- **DB migration:** this adds columns to prod tables. Railway runs `alembic upgrade head` on deploy. **The ship task asks the operator whether to snapshot prod first** (standing rule). Check `alembic heads` (current head `e6f7a8b9c0d1`) and chain from it.
- **Commits:** straight to `main`; body ends `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Backend commands use the shared venv `/Users/leeashmore/Local Repo/.venv`.

## File Structure

- `backend/alembic/versions/<rev>_content_updated_at.py` — migration (new).
- `backend/app/models/content.py` — add `updated_at` to Module/Level/Lesson (modify).
- `backend/app/services/content_serialize.py` — extracted serializers (new) OR add to an existing content service; both the routes and the bundle import them.
- `backend/app/routers/content.py` — routes call the extracted serializers; add the bundle route (modify).
- `backend/app/services/offline_bundle_service.py` — builds the bundle (new).
- `backend/app/schemas/content.py` (or wherever `ModuleOut` etc. live) — `OfflineBundleOut` schema (modify/new).
- `frontend/src/lib/offline/sqlite.ts` — schema v2: add `sync_meta` (modify).
- `frontend/src/lib/offline/contentStore.ts` — `getLastSync`/`setLastSync`/`reconcileIds` (modify).
- `frontend/src/api/content.ts` — `getOfflineBundle(since)` + the `OfflineBundle` type (modify).
- `frontend/src/lib/offline/marketSync.ts` — `syncMarket(scope)` (new).
- `frontend/src/hooks/useOfflineMarketSync.ts` — app-open hook (new).
- `frontend/src/components/child/Shell.tsx` — mount the hook (modify).
- `frontend/src/pages/child/Level.tsx` + `frontend/src/components/child/DownloadLevelButton.tsx` (+ test) — remove the button (modify/delete).

---

### Task 1: `updated_at` migration + ORM columns

**Files:** Create `backend/alembic/versions/<rev>_content_updated_at.py`; Modify `backend/app/models/content.py`.

**Interfaces:**
- Produces: `Module.updated_at`, `Level.updated_at`, `Lesson.updated_at` (`datetime`, non-null, server-default now, ORM `onupdate` now); indexed `ix_lessons_updated_at`.

- [ ] **Step 1:** In `content.py`, add to each of `Module`, `Level`, `Lesson` (mirror the existing `created_at`/timestamp column style in the file):

```python
updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
)
```
(For `Lesson`, also pass `index=True`, or add a separate index in the migration.) Ensure `func`/`DateTime` are imported (they are used elsewhere in the file).

- [ ] **Step 2:** `cd backend && alembic heads` → confirm `e6f7a8b9c0d1`. Create a hand-written migration chained `down_revision = "e6f7a8b9c0d1"`:

```python
def upgrade() -> None:
    for table in ("modules", "levels", "lessons"):
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.text("now()"), nullable=False))
    op.create_index("ix_lessons_updated_at", "lessons", ["updated_at"])

def downgrade() -> None:
    op.drop_index("ix_lessons_updated_at", table_name="lessons")
    for table in ("modules", "levels", "lessons"):
        op.drop_column(table, "updated_at")
```
(The `server_default now()` backfills existing rows to "now" on upgrade — correct: the first post-deploy bundle then returns everything.)

- [ ] **Step 3:** `alembic upgrade head` against the local DB → succeeds; `alembic downgrade -1 && alembic upgrade head` round-trips cleanly. `ruff check backend/` clean. `python -c "import app.main"` OK.

- [ ] **Step 4: Commit** `feat(content): add updated_at to modules/levels/lessons (offline delta)`.

---

### Task 2: Extract serializers + offline-bundle endpoint

**Files:** Create `backend/app/services/offline_bundle_service.py`; Modify `backend/app/routers/content.py`, the schemas module; Test `backend/tests/test_offline_bundle.py`.

**Interfaces:**
- Consumes: `active_market` (`app/core/markets.py`), `is_premium`/`market_locked_for` (`app/services/entitlements.py`), the content models, `updated_at` (Task 1).
- Produces: `GET /content/offline-bundle?since=<iso8601|empty>` → `OfflineBundleOut`.

**Serializer extraction (DRY — do this first):** In `content.py` the routes `list_modules` (~L80), `list_levels` (~L187), `list_level_lessons` (~L248), `get_lesson` (~L291) build `ModuleOut`/`LevelOut`/`LessonSummary`/`LessonOut` inline with per-user logic (visibility, premium, level-state, `completed`). Extract that construction into module-level helpers (e.g. in `content_serialize.py` or as functions reused by the router) — `serialize_modules(user, modules)`, `serialize_levels(user, module, levels, progress)`, `serialize_level_lessons(user, level, lessons, progress)`, `serialize_lesson(user, lesson, progress)` — preserving behaviour EXACTLY, and call them from both the existing routes and the bundle. Confirm the existing content tests still pass after the extraction (behaviour-preserving).

`OfflineBundleOut` (Pydantic):
```python
class OfflineBundleOut(BaseModel):
    market: str
    server_time: str            # ISO8601, server clock
    modules: list[ModuleOut]
    module_levels: dict[str, list[LevelOut]]      # keyed by module id (str)
    level_lessons: dict[str, list[LessonSummary]] # keyed by level id (str)
    lessons: list[LessonOut]                       # changed since `since` (or all)
    current_ids: OfflineBundleIds                   # {modules:[str], levels:[str], lessons:[str]}
```

- [ ] **Step 1: Write the failing test** `backend/tests/test_offline_bundle.py` (async, use the `client`/`admin_client`/`db_session` fixtures + the project's `pytestmark = pytest.mark.asyncio(loop_scope="session")`):
  - `since` empty → `lessons` contains ALL the market's lessons; `current_ids.lessons` matches; `modules`/`module_levels`/`level_lessons` populated; `market` == the child's active market.
  - After bumping one lesson's `updated_at` (edit it), `since=<earlier ts>` → `lessons` contains ONLY that lesson; metadata still full; `current_ids` still complete.
  - A lesson/module from ANOTHER market never appears (market scoping).
  - `server_time` is present + ISO8601-parseable.
  - Unauth request → 401.

- [ ] **Step 2:** Run → FAIL (route missing).

- [ ] **Step 3:** Implement `offline_bundle_service.build_bundle(session, user, since: datetime | None) -> dict` — query the user's active market's modules (visible), their levels, their level-lessons, and lessons (all when `since` is None, else `WHERE updated_at > since`), load the user's progress once, serialize via the extracted helpers, assemble `current_ids` from the full id sets, set `server_time` from the DB clock (`select(func.now())` or `datetime.now(UTC)` — prefer the DB clock for consistency with `updated_at`). Add the route in `content.py`:
```python
@router.get("/offline-bundle", response_model=OfflineBundleOut)
async def offline_bundle(since: str | None = None, current_user=Depends(get_current_user), session=Depends(get_session)):
    parsed = _parse_iso(since) if since else None   # tolerant parse; None on blank/invalid
    return await offline_bundle_service.build_bundle(session, current_user, parsed)
```

- [ ] **Step 4:** Run the new test + the existing content tests (`tests/test_*content*`, `tests/test_*module*`/`*lesson*`/`*level*`) → all green (serializer extraction preserved behaviour). `ruff check backend/` clean.

- [ ] **Step 5: Commit** `feat(content): offline-bundle endpoint (incremental market sync)`.

---

### Task 3: SQLite `sync_meta` + store helpers

**Files:** Modify `frontend/src/lib/offline/sqlite.ts`, `frontend/src/lib/offline/contentStore.ts`; extend `frontend/src/lib/offline/__tests__/contentStore.test.ts`.

**Interfaces:**
- Produces: `getLastSync(scope): Promise<string | null>`, `setLastSync(scope, iso: string): Promise<void>`, `reconcileIds(scope, ids: { modules: string[]; levels: string[]; lessons: string[] }): Promise<void>`.

- [ ] **Step 1:** `sqlite.ts` — bump `DB_VERSION` to `2` and add to the schema string:
```sql
CREATE TABLE IF NOT EXISTS sync_meta (
  child_id TEXT NOT NULL, market TEXT NOT NULL, last_sync TEXT NOT NULL,
  PRIMARY KEY (child_id, market)
);
```
(The `CREATE TABLE IF NOT EXISTS` schema runs on open, so existing installs gain the table without a destructive migration.)

- [ ] **Step 2: Failing tests** (mock `./sqlite`, as the existing contentStore tests do): `setLastSync` then `getLastSync` round-trips per scope; `getLastSync` returns null when absent / unavailable; `reconcileIds` issues a scoped `DELETE … WHERE child_id=? AND market=? AND lesson_id NOT IN (...)` for cached_lesson (and the analogous deletes for cached_level_lessons by level_id, cached_module_levels by module_id), and is a no-op when a given id list is empty-but-present vs absent (decide: an explicitly-empty list means "evict all of that type" — but guard: only run when called from a successful sync). Assert the SQL + scoped params.

- [ ] **Step 3:** Implement the three fns in `contentStore.ts` (same no-op-when-unavailable + try/catch pattern as the existing fns). `reconcileIds`: for each of cached_lesson/cached_level_lessons/cached_module_levels, `DELETE … WHERE child_id=? AND market=? AND <idcol> NOT IN (<placeholders>)` (parameterised; if an id list is empty, delete all of that type for the scope — the caller only passes complete sets).

- [ ] **Step 4:** `npx vitest run src/lib/offline/__tests__/contentStore.test.ts` green; tsc + lint clean.

- [ ] **Step 5: Commit** `feat(offline): sync_meta + reconcileIds for market sync`.

---

### Task 4: `getOfflineBundle` client + `syncMarket`

**Files:** Modify `frontend/src/api/content.ts`; Create `frontend/src/lib/offline/marketSync.ts`; Test `frontend/src/lib/offline/__tests__/marketSync.test.ts`.

**Interfaces:**
- Consumes: `getLastSync`/`setLastSync`/`reconcileIds` + `upsertModules`/`upsertModuleLevels`/`upsertLevelLessons`/`upsertLesson` (contentStore); `scopeFromMe`/`CacheScope`; `isOfflineDbAvailable`.
- Produces: `getOfflineBundle(since: string | null): Promise<OfflineBundle>`; `syncMarket(scope: CacheScope): Promise<void>`.

- [ ] **Step 1:** `content.ts` — add the `OfflineBundle` type (mirror `OfflineBundleOut`) + `getOfflineBundle(since) => apiFetch<OfflineBundle>('/content/offline-bundle' + (since ? \`?since=${encodeURIComponent(since)}\` : ''))`.

- [ ] **Step 2: Failing test** `marketSync.test.ts` (mock `@/api/content` getOfflineBundle + the contentStore fns):
  - First sync: `getLastSync` → null → calls `getOfflineBundle(null)`; upserts modules, each module_levels, each level_lessons, each lesson (with its level id — derive from the bundle: each lesson's `module_id` + the level_lessons mapping, or pass null if not resolvable); calls `reconcileIds(current_ids)`; `setLastSync(server_time)`.
  - Second sync: `getLastSync` → "T" → calls `getOfflineBundle("T")`; applies deltas; `setLastSync(new server_time)`.
  - On `getOfflineBundle` throwing: `syncMarket` does NOT throw, does NOT call `reconcileIds` or `setLastSync` (cache + last_sync untouched).
  - No-op when `!isOfflineDbAvailable()`.

- [ ] **Step 3:** Implement `syncMarket(scope)`: if `!isOfflineDbAvailable()` return; `try { const since = await getLastSync(scope); const b = await getOfflineBundle(since); await upsertModules(scope, b.modules); for (const [mid, levels] of Object.entries(b.module_levels)) await upsertModuleLevels(scope, mid, levels); for (const [lid, lessons] of Object.entries(b.level_lessons)) await upsertLevelLessons(scope, lid, lessons); for (const lesson of b.lessons) await upsertLesson(scope, lesson, <levelId for lesson or null>); await reconcileIds(scope, b.current_ids); await setLastSync(scope, b.server_time); } catch { /* best-effort */ }`. (For the lesson→level mapping, build a `lessonId→levelId` map from `b.level_lessons` before the loop; pass null if a lesson isn't in any level list.)

- [ ] **Step 4:** vitest green; tsc + lint clean; full suite no new failures.

- [ ] **Step 5: Commit** `feat(offline): syncMarket — incremental market bundle into SQLite`.

---

### Task 5: `useOfflineMarketSync` hook + Shell mount

**Files:** Create `frontend/src/hooks/useOfflineMarketSync.ts`; Modify `frontend/src/components/child/Shell.tsx`; Test `frontend/src/hooks/__tests__/useOfflineMarketSync.test.tsx`.

**Interfaces:**
- Consumes: `syncMarket`, `scopeFromMe`, `isOfflineDbAvailable`, `onlineManager` (TanStack), the `['me']` query (via `useQueryClient().getQueryData<Me>(['me'])`).

- [ ] **Step 1: Failing test:** the hook calls `syncMarket(scope)` once when native + online + scope present; does NOT call it on web (`isOfflineDbAvailable` false), when offline (`onlineManager.isOnline()` false), or when scope is null; calls it at most once per mount (guard ref). Mock `@/lib/offline/marketSync`, `@/lib/offline/sqlite`, `@tanstack/react-query`'s `onlineManager`.

- [ ] **Step 2:** Run → FAIL.

- [ ] **Step 3:** Implement: a `useEffect` (run after `me` is available) that, guarded by a `useRef(false)` "ran this session" flag, checks `isOfflineDbAvailable() && onlineManager.isOnline()` and a non-null `scope = scopeFromMe(qc.getQueryData<Me>(['me']))`, then `void syncMarket(scope)` (fire-and-forget — never blocks). Depend on `[scope?.childId, scope?.market]` so a market switch re-syncs (reset the ref when the scope changes).

- [ ] **Step 4:** Mount `useOfflineMarketSync()` in `Shell.tsx` (after `session.data` is available — alongside the other top-level hooks). Test green; tsc + lint; full suite no new failures.

- [ ] **Step 5: Commit** `feat(offline): auto-sync the active market on app open`.

---

### Task 6: Remove the manual download button

**Files:** Modify `frontend/src/pages/child/Level.tsx`; Delete `frontend/src/components/child/DownloadLevelButton.tsx` + `frontend/src/components/child/__tests__/DownloadLevelButton.test.tsx`; Modify `frontend/src/locales/en/child.json`.

- [ ] **Step 1:** Remove the `DownloadLevelButton` import + its `<DownloadLevelButton …/>` mount from `Level.tsx` (~L14, L139). `git rm` the component + its test.
- [ ] **Step 2:** Remove the now-unused i18n keys `offline.download` + `offline.saving` from `child.json` (keep `offline.available` — still used by `OfflineBadge`). Grep to confirm no remaining references to the removed keys or component.
- [ ] **Step 3:** `npx tsc --noEmit` clean; `npm run lint` 0 errors; full `npx vitest run` — confirm the failing set equals the known baseline (the deleted test is gone; nothing else references the component).
- [ ] **Step 4: Commit** `refactor(offline): drop per-level download button (market auto-syncs)`.

---

### Task 7: Full verify + ship + docs

**Files:** Modify `docs/MASTER-BACKLOG.md`.

- [ ] **Step 1:** Backend: `ruff check backend/` clean; run the offline-bundle + content + migration round-trip tests green. Frontend: `npx tsc --noEmit`, `npm run lint` 0 errors, full `npx vitest run` baseline-unchanged, `npm run build` clean.
- [ ] **Step 2: PROD MIGRATION — ASK FIRST.** This deploy runs `alembic upgrade head` adding `updated_at` to modules/levels/lessons on the prod DB. **Ask the operator whether to take a prod snapshot before pushing** (standing rule). Only push after their answer.
- [ ] **Step 3:** Push → watch CI (`gh run view <id> --json status,conclusion,jobs`; Backend + Frontend both run) → all green. Railway auto-deploys the backend (runs the migration).
- [ ] **Step 4:** Vercel two-step (`vercel --prod --yes` from `frontend/` → `vercel alias set <hash>-investikid.vercel.app app.investikid.ai` → `curl` → 200). `npx cap sync` (iOS-visible) — native rebuild flagged as operator follow-up.
- [ ] **Step 5:** Update `docs/MASTER-BACKLOG.md` (Goal 4 Phase 3b done). Commit `docs: mark Goal 4 Phase 3b shipped` + push.

---

## Notes for the executor

- **The serializer extraction (Task 2) is the crux** — the bundle's offline snapshots must match what the per-item routes return, or offline `completed`/level-state/premium state will diverge. Extract + reuse; don't write a second serializer. Confirm the existing content tests stay green as the proof.
- Stale per-child `completed`/level-state in the offline snapshot is acceptable (Phase 3 precedent) — the delta is content-only (`updated_at`); the online `cacheFirst` path refreshes it.
- Best-effort + eviction-only-on-success: a flaky sync must never wipe or corrupt the cache.
- CI-safety: verify frontend lint with `npm run lint` (= `eslint .`); before any push run the FULL `npx vitest run` and confirm the failing set equals the ~68 local-env baseline.
