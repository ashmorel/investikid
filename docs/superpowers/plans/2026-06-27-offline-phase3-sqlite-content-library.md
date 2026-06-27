# Offline Phase 3 — SQLite Content Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move offline caching of learning content (modules, levels, lessons) into a structured, native-only SQLite store with cache-first write-through, and surface it to the child as an "available offline" library — without touching the shipped Phase 2b outbox or the web persister.

**Architecture:** A thin async DAL (`contentStore`) over `@capacitor-community/sqlite`, scoped by `(child_id, market)`, behind a `getDb()`/`isOfflineDbAvailable()` boundary that no-ops on web and on any device where the DB can't open. Content `queryFn`s become cache-first: fetch → upsert on success → read SQLite on offline failure. On native, content keys drop out of the localStorage persist blob (relieving the ~5MB cap). The Phase 2b TanStack completion outbox and the web persister are unchanged.

**Tech Stack:** React 18, TanStack Query 5, Capacitor 8 (`@capacitor-community/sqlite`), TypeScript, Vite, vitest, vitest-axe.

## Global Constraints

- **Native-only SQLite.** Web has no SQLite; do NOT add `jeep-sqlite`. On web / unavailable DB, every offline-store call no-ops and callers fall back to network/RQ. Gate on `isOfflineDbAvailable()` (= `isNativeApp()` from `@/lib/platform` AND plugin usable).
- **Do not touch** `frontend/src/lib/offlineMutations.ts` (Phase 2b outbox) or the web persister behavior. Phase 1/2a/2b semantics on web stay byte-identical.
- **Scope every row by `(child_id, market)`.** `child_id` = `me.id`; `market` = `me.active_market_code ?? me.content_region ?? 'US'` (from the `['me']` query, type `Me` in `src/api/auth.ts`). Never read/write unscoped.
- **No `as any`.** CI runs `npm run lint` (= `eslint .`); `@typescript-eslint/no-explicit-any` is error-level. Use `as unknown as T` and real types in tests.
- **Staleness:** `OFFLINE_MAX_AGE = 24 * 60 * 60 * 1000` (matches `PERSIST_MAX_AGE`). A row older than this is a *fallback* miss but is still overwritten on the next online fetch.
- **No encryption** (public learning content, no PII): `createConnection(name, false, 'no-encryption', 1, false)`.
- **Verification per task (from `frontend/`):** `npx vitest run <file>`, `npx tsc --noEmit`, `npm run lint`. Final task also `npm run build`.
- **Commits:** straight to `main`; end every commit body with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- **UI (Tasks 10–12) is Figma-first:** their markup follows the approved mockups from Task 9. Logic + tests are specified here regardless.

## File Structure

- `frontend/src/lib/offline/sqlite.ts` — DB connection boundary: `isOfflineDbAvailable()`, `getDb()`, schema, `OFFLINE_MAX_AGE`. (new)
- `frontend/src/lib/offline/contentStore.ts` — the scoped DAL: upsert/get for modules/module-levels/level-lessons/lesson, `listAvailableOffline`, `clearForChild`. (new)
- `frontend/src/lib/offline/scope.ts` — derive `{ childId, market }` from a `Me` (shared, pure). (new)
- `frontend/src/lib/offline/useOfflineContent.ts` — `cacheFirst()` write-through wrapper for a `queryFn`. (new)
- `frontend/src/pages/child/{Lessons,Module,Level,Lesson}.tsx` — wrap content `queryFn`s with `cacheFirst`. (modify)
- `frontend/src/hooks/usePrefetchLevelLessons.ts` — write-through prefetch. (modify)
- `frontend/src/lib/queryPersistence.ts` + `frontend/src/main.tsx` — native content-key trim. (modify)
- `frontend/src/components/child/ProfileMenu.tsx` — `clearForChild()` on logout; region/market-switch clear. (modify)
- `frontend/src/components/child/OfflineBadge.tsx` + a downloaded-content view + a "download this level" action (Tasks 10–12). (new)
- `frontend/package.json`, `frontend/capacitor.config.ts` — plugin (Task 8). (modify)

---

### Task 1: SQLite connection boundary (`sqlite.ts`)

**Files:**
- Create: `frontend/src/lib/offline/sqlite.ts`
- Test: `frontend/src/lib/offline/__tests__/sqlite.test.ts`

**Interfaces:**
- Consumes: `isNativeApp()` from `@/lib/platform`; `CapacitorSQLite`, `SQLiteConnection`, `SQLiteDBConnection` from `@capacitor-community/sqlite` (added in Task 8 — for Task 1 it's a dev/types dependency; install it first if absent, see Task 8 step, or add the dep now so types resolve).
- Produces:
  - `export const OFFLINE_MAX_AGE: number`
  - `export function isOfflineDbAvailable(): boolean`
  - `export async function getDb(): Promise<SQLiteDBConnection | null>` (opens lazily, runs `CREATE TABLE IF NOT EXISTS` schema once, returns a shared connection; returns `null` on any failure or when unavailable)
  - `export function __resetDbForTests(): void` (clears the memoized connection between tests)

> **Note:** add `@capacitor-community/sqlite` to `frontend/package.json` deps now (so imports/types resolve for Tasks 1–7); the native `cap sync` happens in Task 8. Run `npm install @capacitor-community/sqlite` in `frontend/` before Step 1.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/offline/__tests__/sqlite.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/lib/platform', () => ({ isNativeApp: vi.fn() }));

// Fake plugin surface
const fakeDb = {
  open: vi.fn(async () => {}),
  execute: vi.fn(async () => ({ changes: { changes: 0 } })),
};
const conn = {
  checkConnectionsConsistency: vi.fn(async () => ({ result: false })),
  isConnection: vi.fn(async () => ({ result: false })),
  retrieveConnection: vi.fn(async () => fakeDb),
  createConnection: vi.fn(async () => fakeDb),
};
vi.mock('@capacitor-community/sqlite', () => ({
  CapacitorSQLite: {},
  SQLiteConnection: vi.fn(() => conn),
}));

import { isNativeApp } from '@/lib/platform';
import { isOfflineDbAvailable, getDb, __resetDbForTests, OFFLINE_MAX_AGE } from '../sqlite';

const mockNative = vi.mocked(isNativeApp);

beforeEach(() => {
  vi.clearAllMocks();
  __resetDbForTests();
});

describe('sqlite boundary', () => {
  it('OFFLINE_MAX_AGE is 24h', () => {
    expect(OFFLINE_MAX_AGE).toBe(24 * 60 * 60 * 1000);
  });

  it('isOfflineDbAvailable is false on web', () => {
    mockNative.mockReturnValue(false);
    expect(isOfflineDbAvailable()).toBe(false);
  });

  it('getDb returns null on web without touching the plugin', async () => {
    mockNative.mockReturnValue(false);
    expect(await getDb()).toBeNull();
    expect(conn.createConnection).not.toHaveBeenCalled();
  });

  it('getDb opens + runs schema on native, and memoizes', async () => {
    mockNative.mockReturnValue(true);
    const db1 = await getDb();
    expect(db1).toBe(fakeDb);
    expect(fakeDb.open).toHaveBeenCalledTimes(1);
    expect(fakeDb.execute).toHaveBeenCalledTimes(1); // schema once
    const schemaSql = fakeDb.execute.mock.calls[0][0] as string;
    expect(schemaSql).toContain('CREATE TABLE IF NOT EXISTS cached_lesson');
    const db2 = await getDb();
    expect(db2).toBe(fakeDb);
    expect(fakeDb.open).toHaveBeenCalledTimes(1); // memoized, not reopened
  });

  it('getDb returns null when open throws', async () => {
    mockNative.mockReturnValue(true);
    fakeDb.open.mockRejectedValueOnce(new Error('locked'));
    expect(await getDb()).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/sqlite.test.ts`
Expected: FAIL (module `../sqlite` not found).

- [ ] **Step 3: Write the implementation**

```ts
// frontend/src/lib/offline/sqlite.ts
import { CapacitorSQLite, SQLiteConnection, type SQLiteDBConnection } from '@capacitor-community/sqlite';
import { isNativeApp } from '@/lib/platform';

/** Fallback-read staleness window; matches PERSIST_MAX_AGE. */
export const OFFLINE_MAX_AGE = 24 * 60 * 60 * 1000;

const DB_NAME = 'investikid';
const DB_VERSION = 1;

/** Schema v1. All content tables are scoped by (child_id, market). */
const SCHEMA = `
CREATE TABLE IF NOT EXISTS cached_modules (
  child_id TEXT NOT NULL, market TEXT NOT NULL,
  payload_json TEXT NOT NULL, cached_at INTEGER NOT NULL,
  PRIMARY KEY (child_id, market)
);
CREATE TABLE IF NOT EXISTS cached_module_levels (
  child_id TEXT NOT NULL, market TEXT NOT NULL, module_id TEXT NOT NULL,
  payload_json TEXT NOT NULL, cached_at INTEGER NOT NULL,
  PRIMARY KEY (child_id, market, module_id)
);
CREATE TABLE IF NOT EXISTS cached_level_lessons (
  child_id TEXT NOT NULL, market TEXT NOT NULL, level_id TEXT NOT NULL,
  payload_json TEXT NOT NULL, cached_at INTEGER NOT NULL,
  PRIMARY KEY (child_id, market, level_id)
);
CREATE TABLE IF NOT EXISTS cached_lesson (
  child_id TEXT NOT NULL, market TEXT NOT NULL, lesson_id TEXT NOT NULL,
  level_id TEXT, payload_json TEXT NOT NULL, cached_at INTEGER NOT NULL,
  PRIMARY KEY (child_id, market, lesson_id)
);
`;

let dbPromise: Promise<SQLiteDBConnection | null> | null = null;

/** True only on a native device where the SQLite plugin is usable. */
export function isOfflineDbAvailable(): boolean {
  return isNativeApp();
}

async function openDb(): Promise<SQLiteDBConnection | null> {
  try {
    const sqlite = new SQLiteConnection(CapacitorSQLite);
    const consistent = (await sqlite.checkConnectionsConsistency()).result;
    const isConn = (await sqlite.isConnection(DB_NAME, false)).result;
    const db = consistent && isConn
      ? await sqlite.retrieveConnection(DB_NAME, false)
      : await sqlite.createConnection(DB_NAME, false, 'no-encryption', DB_VERSION, false);
    await db.open();
    await db.execute(SCHEMA);
    return db;
  } catch {
    return null;
  }
}

/** Lazily open the shared DB, running the schema once. Null when unavailable. */
export function getDb(): Promise<SQLiteDBConnection | null> {
  if (!isOfflineDbAvailable()) return Promise.resolve(null);
  if (!dbPromise) dbPromise = openDb();
  return dbPromise;
}

/** Test-only: drop the memoized connection. */
export function __resetDbForTests(): void {
  dbPromise = null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/sqlite.test.ts`
Expected: PASS (5 tests). Then `npx tsc --noEmit` and `npm run lint` clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/offline/sqlite.ts frontend/src/lib/offline/__tests__/sqlite.test.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(offline): SQLite connection boundary + schema (Phase 3)"
```

---

### Task 2: Scope helper (`scope.ts`)

**Files:**
- Create: `frontend/src/lib/offline/scope.ts`
- Test: `frontend/src/lib/offline/__tests__/scope.test.ts`

**Interfaces:**
- Consumes: `Me` type from `@/api/auth` (`id: string`, `active_market_code?: string`, `content_region: string | null`).
- Produces: `export type CacheScope = { childId: string; market: string }`; `export function scopeFromMe(me: Me | null | undefined): CacheScope | null` — returns null when `me` or `me.id` absent; else `{ childId: me.id, market: me.active_market_code ?? me.content_region ?? 'US' }`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/offline/__tests__/scope.test.ts
import { describe, it, expect } from 'vitest';
import type { Me } from '@/api/auth';
import { scopeFromMe } from '../scope';

const base = { id: 'C1' } as unknown as Me;

describe('scopeFromMe', () => {
  it('prefers active_market_code', () => {
    expect(scopeFromMe({ ...base, active_market_code: 'GB' } as Me))
      .toEqual({ childId: 'C1', market: 'GB' });
  });
  it('falls back to content_region then US', () => {
    expect(scopeFromMe({ ...base, content_region: 'HK' } as Me))
      .toEqual({ childId: 'C1', market: 'HK' });
    expect(scopeFromMe(base)).toEqual({ childId: 'C1', market: 'US' });
  });
  it('returns null without an id', () => {
    expect(scopeFromMe(null)).toBeNull();
    expect(scopeFromMe({} as Me)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/scope.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

```ts
// frontend/src/lib/offline/scope.ts
import type { Me } from '@/api/auth';

export type CacheScope = { childId: string; market: string };

/** Derive the (child, market) cache scope from the `me` payload, or null. */
export function scopeFromMe(me: Me | null | undefined): CacheScope | null {
  if (!me || !me.id) return null;
  return { childId: me.id, market: me.active_market_code ?? me.content_region ?? 'US' };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/scope.test.ts` → PASS (3). Then tsc + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/offline/scope.ts frontend/src/lib/offline/__tests__/scope.test.ts
git commit -m "feat(offline): (child, market) cache-scope helper"
```

---

### Task 3: Content store DAL — upsert/get (`contentStore.ts`)

**Files:**
- Create: `frontend/src/lib/offline/contentStore.ts`
- Test: `frontend/src/lib/offline/__tests__/contentStore.test.ts`

**Interfaces:**
- Consumes: `getDb`, `isOfflineDbAvailable`, `OFFLINE_MAX_AGE` from `./sqlite`; `CacheScope` from `./scope`; content types from `@/api/content` (`ModuleOut[]`, `LevelOut[]`, `LessonSummary[]`, `LessonOut`).
- Produces (all async, all no-op→`null` when `!isOfflineDbAvailable()`, all try/catch→`null` on error; `now` is injectable for tests):
  - `upsertModules(scope, payload: ModuleOut[], now?: number): Promise<void>`
  - `getModules(scope, now?: number): Promise<ModuleOut[] | null>`
  - `upsertModuleLevels(scope, moduleId, payload: LevelOut[], now?): Promise<void>`
  - `getModuleLevels(scope, moduleId, now?): Promise<LevelOut[] | null>`
  - `upsertLevelLessons(scope, levelId, payload: LessonSummary[], now?): Promise<void>`
  - `getLevelLessons(scope, levelId, now?): Promise<LessonSummary[] | null>`
  - `upsertLesson(scope, lesson: LessonOut, levelId: string | null, now?): Promise<void>`
  - `getLesson(scope, lessonId, now?): Promise<LessonOut | null>`

> A `get*` returns `null` when there is no row OR the row is older than `OFFLINE_MAX_AGE` (treated as a miss). Upserts always overwrite (`INSERT … ON CONFLICT(pk) DO UPDATE SET payload_json=excluded.payload_json, cached_at=excluded.cached_at`). `now` defaults to `Date.now()` — note `Date.now()` is fine in app code (the no-`Date.now` rule is only for Workflow scripts).

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/offline/__tests__/contentStore.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

const run = vi.fn(async () => ({ changes: { changes: 1 } }));
const query = vi.fn(async () => ({ values: [] as unknown[] }));
const fakeDb = { run, query };

vi.mock('../sqlite', () => ({
  OFFLINE_MAX_AGE: 24 * 60 * 60 * 1000,
  isOfflineDbAvailable: vi.fn(() => true),
  getDb: vi.fn(async () => fakeDb),
}));

import { isOfflineDbAvailable, getDb } from '../sqlite';
import type { CacheScope } from '../scope';
import * as store from '../contentStore';
import type { LessonOut, ModuleOut } from '@/api/content';

const scope: CacheScope = { childId: 'C1', market: 'GB' };
beforeEach(() => vi.clearAllMocks());

describe('contentStore', () => {
  it('upsertLesson writes a scoped, parameterised UPSERT with level_id + cached_at', async () => {
    const lesson = { id: 'L1' } as unknown as LessonOut;
    await store.upsertLesson(scope, lesson, 'LV1', 1000);
    expect(run).toHaveBeenCalledTimes(1);
    const [sql, values] = run.mock.calls[0];
    expect(sql).toContain('INTO cached_lesson');
    expect(sql).toContain('ON CONFLICT');
    expect(values).toEqual(['C1', 'GB', 'L1', 'LV1', JSON.stringify(lesson), 1000]);
  });

  it('getLesson returns the parsed payload for a fresh row', async () => {
    query.mockResolvedValueOnce({ values: [{ payload_json: JSON.stringify({ id: 'L1' }), cached_at: 1000 }] });
    const out = await store.getLesson(scope, 'L1', 1000);
    expect(out).toEqual({ id: 'L1' });
    const [sql, values] = query.mock.calls[0];
    expect(sql).toContain('FROM cached_lesson');
    expect(values).toEqual(['C1', 'GB', 'L1']);
  });

  it('getLesson returns null for a stale row (older than max age)', async () => {
    query.mockResolvedValueOnce({ values: [{ payload_json: JSON.stringify({ id: 'L1' }), cached_at: 0 }] });
    const out = await store.getLesson(scope, 'L1', 24 * 60 * 60 * 1000 + 1);
    expect(out).toBeNull();
  });

  it('getModules returns null when no row', async () => {
    query.mockResolvedValueOnce({ values: [] });
    expect(await store.getModules(scope, 1000)).toBeNull();
  });

  it('upsertModules round-trips an array payload', async () => {
    const mods = [{ id: 'M1' }] as unknown as ModuleOut[];
    await store.upsertModules(scope, mods, 1000);
    const [, values] = run.mock.calls[0];
    expect(values).toEqual(['C1', 'GB', JSON.stringify(mods), 1000]);
  });

  it('no-ops to null/void when the DB is unavailable', async () => {
    vi.mocked(isOfflineDbAvailable).mockReturnValueOnce(false);
    expect(await store.getLesson(scope, 'L1', 1000)).toBeNull();
    expect(getDb).not.toHaveBeenCalled();
  });

  it('swallows DB errors and returns null', async () => {
    query.mockRejectedValueOnce(new Error('disk'));
    expect(await store.getModules(scope, 1000)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/contentStore.test.ts`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

```ts
// frontend/src/lib/offline/contentStore.ts
import type { LessonOut, LessonSummary, LevelOut, ModuleOut } from '@/api/content';
import type { CacheScope } from './scope';
import { getDb, isOfflineDbAvailable, OFFLINE_MAX_AGE } from './sqlite';

type Row = { payload_json: string; cached_at: number };

async function upsert(sql: string, values: unknown[]): Promise<void> {
  if (!isOfflineDbAvailable()) return;
  try {
    const db = await getDb();
    if (!db) return;
    await db.run(sql, values);
  } catch {
    /* best-effort cache; ignore */
  }
}

async function readFresh<T>(sql: string, values: unknown[], now: number): Promise<T | null> {
  if (!isOfflineDbAvailable()) return null;
  try {
    const db = await getDb();
    if (!db) return null;
    const res = await db.query(sql, values);
    const row = (res.values?.[0] ?? null) as Row | null;
    if (!row) return null;
    if (now - row.cached_at > OFFLINE_MAX_AGE) return null;
    return JSON.parse(row.payload_json) as T;
  } catch {
    return null;
  }
}

// --- modules (one row per scope) ---
export function upsertModules(scope: CacheScope, payload: ModuleOut[], now: number = Date.now()): Promise<void> {
  return upsert(
    `INSERT INTO cached_modules (child_id, market, payload_json, cached_at) VALUES (?,?,?,?)
     ON CONFLICT(child_id, market) DO UPDATE SET payload_json=excluded.payload_json, cached_at=excluded.cached_at`,
    [scope.childId, scope.market, JSON.stringify(payload), now],
  );
}
export function getModules(scope: CacheScope, now: number = Date.now()): Promise<ModuleOut[] | null> {
  return readFresh<ModuleOut[]>(
    `SELECT payload_json, cached_at FROM cached_modules WHERE child_id=? AND market=?`,
    [scope.childId, scope.market], now,
  );
}

// --- module-levels (one row per module) ---
export function upsertModuleLevels(scope: CacheScope, moduleId: string, payload: LevelOut[], now: number = Date.now()): Promise<void> {
  return upsert(
    `INSERT INTO cached_module_levels (child_id, market, module_id, payload_json, cached_at) VALUES (?,?,?,?,?)
     ON CONFLICT(child_id, market, module_id) DO UPDATE SET payload_json=excluded.payload_json, cached_at=excluded.cached_at`,
    [scope.childId, scope.market, moduleId, JSON.stringify(payload), now],
  );
}
export function getModuleLevels(scope: CacheScope, moduleId: string, now: number = Date.now()): Promise<LevelOut[] | null> {
  return readFresh<LevelOut[]>(
    `SELECT payload_json, cached_at FROM cached_module_levels WHERE child_id=? AND market=? AND module_id=?`,
    [scope.childId, scope.market, moduleId], now,
  );
}

// --- level-lessons (one row per level) ---
export function upsertLevelLessons(scope: CacheScope, levelId: string, payload: LessonSummary[], now: number = Date.now()): Promise<void> {
  return upsert(
    `INSERT INTO cached_level_lessons (child_id, market, level_id, payload_json, cached_at) VALUES (?,?,?,?,?)
     ON CONFLICT(child_id, market, level_id) DO UPDATE SET payload_json=excluded.payload_json, cached_at=excluded.cached_at`,
    [scope.childId, scope.market, levelId, JSON.stringify(payload), now],
  );
}
export function getLevelLessons(scope: CacheScope, levelId: string, now: number = Date.now()): Promise<LessonSummary[] | null> {
  return readFresh<LessonSummary[]>(
    `SELECT payload_json, cached_at FROM cached_level_lessons WHERE child_id=? AND market=? AND level_id=?`,
    [scope.childId, scope.market, levelId], now,
  );
}

// --- lesson (one row per lesson, level_id denormalised for availability) ---
export function upsertLesson(scope: CacheScope, lesson: LessonOut, levelId: string | null, now: number = Date.now()): Promise<void> {
  return upsert(
    `INSERT INTO cached_lesson (child_id, market, lesson_id, level_id, payload_json, cached_at) VALUES (?,?,?,?,?,?)
     ON CONFLICT(child_id, market, lesson_id) DO UPDATE SET level_id=excluded.level_id, payload_json=excluded.payload_json, cached_at=excluded.cached_at`,
    [scope.childId, scope.market, lesson.id, levelId, JSON.stringify(lesson), now],
  );
}
export function getLesson(scope: CacheScope, lessonId: string, now: number = Date.now()): Promise<LessonOut | null> {
  return readFresh<LessonOut>(
    `SELECT payload_json, cached_at FROM cached_lesson WHERE child_id=? AND market=? AND lesson_id=?`,
    [scope.childId, scope.market, lessonId], now,
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/contentStore.test.ts` → PASS (7). Then tsc + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/offline/contentStore.ts frontend/src/lib/offline/__tests__/contentStore.test.ts
git commit -m "feat(offline): scoped content-store DAL (upsert/get)"
```

---

### Task 4: Availability + clear (`listAvailableOffline`, `clearForChild`)

**Files:**
- Modify: `frontend/src/lib/offline/contentStore.ts`
- Modify: `frontend/src/lib/offline/__tests__/contentStore.test.ts`

**Interfaces:**
- Produces:
  - `export type OfflineAvailability = { levelIds: string[]; lessonCount: number }`
  - `listAvailableOffline(scope, now?): Promise<OfflineAvailability>` — distinct `level_id`s present in `cached_lesson` (fresh rows only) + total fresh lesson count. Returns `{ levelIds: [], lessonCount: 0 }` when unavailable/empty/error.
  - `clearForChild(scope): Promise<void>` — `DELETE` all four tables WHERE `child_id=? AND market=?`. No-op when unavailable; swallows errors.

- [ ] **Step 1: Add failing tests**

```ts
// append to contentStore.test.ts
describe('availability + clear', () => {
  it('listAvailableOffline returns distinct fresh level ids + count', async () => {
    query.mockResolvedValueOnce({ values: [{ level_id: 'LV1' }, { level_id: 'LV2' }] }); // distinct levels
    query.mockResolvedValueOnce({ values: [{ n: 3 }] }); // count
    const a = await store.listAvailableOffline(scope, 1000);
    expect(a).toEqual({ levelIds: ['LV1', 'LV2'], lessonCount: 3 });
  });

  it('listAvailableOffline returns empty when unavailable', async () => {
    vi.mocked(isOfflineDbAvailable).mockReturnValueOnce(false);
    expect(await store.listAvailableOffline(scope, 1000)).toEqual({ levelIds: [], lessonCount: 0 });
  });

  it('clearForChild deletes from all four tables for the scope', async () => {
    await store.clearForChild(scope);
    expect(run).toHaveBeenCalledTimes(4);
    for (const call of run.mock.calls) {
      expect(call[1]).toEqual(['C1', 'GB']);
      expect(call[0]).toContain('DELETE FROM cached_');
    }
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/contentStore.test.ts`
Expected: FAIL (`listAvailableOffline`/`clearForChild` not exported).

- [ ] **Step 3: Implement (append to `contentStore.ts`)**

```ts
export type OfflineAvailability = { levelIds: string[]; lessonCount: number };

export async function listAvailableOffline(scope: CacheScope, now: number = Date.now()): Promise<OfflineAvailability> {
  const empty: OfflineAvailability = { levelIds: [], lessonCount: 0 };
  if (!isOfflineDbAvailable()) return empty;
  try {
    const db = await getDb();
    if (!db) return empty;
    const minTs = now - OFFLINE_MAX_AGE;
    const levels = await db.query(
      `SELECT DISTINCT level_id FROM cached_lesson WHERE child_id=? AND market=? AND level_id IS NOT NULL AND cached_at>?`,
      [scope.childId, scope.market, minTs],
    );
    const count = await db.query(
      `SELECT COUNT(*) AS n FROM cached_lesson WHERE child_id=? AND market=? AND cached_at>?`,
      [scope.childId, scope.market, minTs],
    );
    const levelIds = (levels.values ?? []).map((r) => (r as { level_id: string }).level_id);
    const lessonCount = Number((count.values?.[0] as { n: number } | undefined)?.n ?? 0);
    return { levelIds, lessonCount };
  } catch {
    return empty;
  }
}

export async function clearForChild(scope: CacheScope): Promise<void> {
  if (!isOfflineDbAvailable()) return;
  try {
    const db = await getDb();
    if (!db) return;
    for (const table of ['cached_modules', 'cached_module_levels', 'cached_level_lessons', 'cached_lesson']) {
      await db.run(`DELETE FROM ${table} WHERE child_id=? AND market=?`, [scope.childId, scope.market]);
    }
  } catch {
    /* ignore */
  }
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && npx vitest run src/lib/offline/__tests__/contentStore.test.ts` → PASS (10). tsc + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/offline/contentStore.ts frontend/src/lib/offline/__tests__/contentStore.test.ts
git commit -m "feat(offline): listAvailableOffline + clearForChild"
```

---

### Task 5: Cache-first write-through wrapper (`useOfflineContent.ts`)

**Files:**
- Create: `frontend/src/lib/offline/useOfflineContent.ts`
- Test: `frontend/src/lib/offline/__tests__/useOfflineContent.test.ts`

**Interfaces:**
- Consumes: `isOfflineDbAvailable` from `./sqlite`; `CacheScope` from `./scope`.
- Produces: `export function cacheFirst<T>(opts: { scope: CacheScope | null; fetch: () => Promise<T>; read: (scope: CacheScope) => Promise<T | null>; write: (scope: CacheScope, data: T) => Promise<void>; }): () => Promise<T>` — returns a `queryFn`. Behavior: call `fetch()`; on success, if `scope` and available, `void write(scope, data)` (fire-and-forget) and return data; on a thrown error, if `scope` and available, try `read(scope)` and return it when non-null, else rethrow the original error.

> Why a factory not a hook: it composes into existing `useQuery({ queryFn })` call sites without changing their `queryKey`/options. The "use" prefix is avoided deliberately (it's not a hook) — name it `cacheFirst`.

- [ ] **Step 1: Write the failing test**

```ts
// frontend/src/lib/offline/__tests__/useOfflineContent.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
vi.mock('../sqlite', () => ({ isOfflineDbAvailable: vi.fn(() => true) }));
import { isOfflineDbAvailable } from '../sqlite';
import type { CacheScope } from '../scope';
import { cacheFirst } from '../useOfflineContent';

const scope: CacheScope = { childId: 'C1', market: 'GB' };
beforeEach(() => vi.clearAllMocks());

describe('cacheFirst', () => {
  it('online: fetches, writes through, returns data', async () => {
    const write = vi.fn(async () => {});
    const read = vi.fn(async () => null);
    const fn = cacheFirst({ scope, fetch: async () => ({ id: 'L1' }), read, write });
    expect(await fn()).toEqual({ id: 'L1' });
    expect(write).toHaveBeenCalledWith(scope, { id: 'L1' });
    expect(read).not.toHaveBeenCalled();
  });

  it('offline: fetch fails, returns cached read', async () => {
    const fn = cacheFirst({ scope, fetch: async () => { throw new Error('net'); }, read: async () => ({ id: 'cached' }), write: async () => {} });
    expect(await fn()).toEqual({ id: 'cached' });
  });

  it('offline + no cache: rethrows the original error', async () => {
    const err = new Error('net');
    const fn = cacheFirst({ scope, fetch: async () => { throw err; }, read: async () => null, write: async () => {} });
    await expect(fn()).rejects.toBe(err);
  });

  it('unavailable / null scope: passes through fetch, no read/write', async () => {
    vi.mocked(isOfflineDbAvailable).mockReturnValue(false);
    const write = vi.fn(async () => {});
    const fn = cacheFirst({ scope: null, fetch: async () => ({ id: 'L1' }), read: async () => null, write });
    expect(await fn()).toEqual({ id: 'L1' });
    expect(write).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify it fails** → module not found.

- [ ] **Step 3: Implement**

```ts
// frontend/src/lib/offline/useOfflineContent.ts
import type { CacheScope } from './scope';
import { isOfflineDbAvailable } from './sqlite';

export function cacheFirst<T>(opts: {
  scope: CacheScope | null;
  fetch: () => Promise<T>;
  read: (scope: CacheScope) => Promise<T | null>;
  write: (scope: CacheScope, data: T) => Promise<void>;
}): () => Promise<T> {
  const { scope, fetch, read, write } = opts;
  return async () => {
    const useStore = scope != null && isOfflineDbAvailable();
    try {
      const data = await fetch();
      if (useStore) void write(scope, data);
      return data;
    } catch (err) {
      if (useStore) {
        const cached = await read(scope);
        if (cached != null) return cached;
      }
      throw err;
    }
  };
}
```

- [ ] **Step 4: Run to verify it passes** → PASS (4). tsc + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/offline/useOfflineContent.ts frontend/src/lib/offline/__tests__/useOfflineContent.test.ts
git commit -m "feat(offline): cacheFirst write-through queryFn wrapper"
```

---

### Task 6: Wire content queries + prefetch to the store

**Files:**
- Modify: `frontend/src/pages/child/Lessons.tsx` (`['modules']` query, line ~17)
- Modify: `frontend/src/pages/child/Module.tsx` (`['modules']`, `['module-levels', moduleId]`)
- Modify: `frontend/src/pages/child/Level.tsx` (`['level-lessons', levelId]`, `['module-levels', moduleId]`)
- Modify: `frontend/src/pages/child/Lesson.tsx` (`['lesson', lessonId]`, `['level-lessons', levelId]`, `['modules']`, `['module-levels', moduleId]`)
- Modify: `frontend/src/hooks/usePrefetchLevelLessons.ts`
- Test: `frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx` (extend)

**Interfaces:**
- Consumes: `cacheFirst` (Task 5), `scopeFromMe` (Task 2), content store fns (Tasks 3–4). The active scope comes from the `['me']` query already present on these pages (or read via `queryClient.getQueryData<Me>(['me'])` where `me` isn't already loaded).

**Pattern for each page** — get `scope` once near the top, then wrap each content `queryFn`. Example for `Lesson.tsx` (the `['lesson']` query). Current code:

```tsx
const lessonQ = useQuery({
  queryKey: ['lesson', lessonId],
  queryFn: () => contentApi.getLesson(lessonId!),
  // ...existing options
});
```

becomes:

```tsx
import { scopeFromMe } from '@/lib/offline/scope';
import { cacheFirst } from '@/lib/offline/useOfflineContent';
import * as offlineStore from '@/lib/offline/contentStore';
// ...
const meForScope = qc.getQueryData<Me>(['me']);     // qc = useQueryClient(); Me from '@/api/auth'
const scope = scopeFromMe(meForScope);

const lessonQ = useQuery({
  queryKey: ['lesson', lessonId],
  queryFn: cacheFirst({
    scope,
    fetch: () => contentApi.getLesson(lessonId!),
    read: (s) => offlineStore.getLesson(s, lessonId!),
    write: (s, data) => offlineStore.upsertLesson(s, data, levelId ?? null),
  }),
  // ...existing options unchanged
});
```

Apply the analogous wrap to every content query listed in **Files** using the matching store fns:
- `['modules']` → `read: getModules`, `write: upsertModules`
- `['module-levels', moduleId]` → `read: (s)=>getModuleLevels(s, moduleId!)`, `write: (s,d)=>upsertModuleLevels(s, moduleId!, d)`
- `['level-lessons', levelId]` → `read: (s)=>getLevelLessons(s, levelId!)`, `write: (s,d)=>upsertLevelLessons(s, levelId!, d)`
- `['lesson', id]` → as above; `levelId` is in scope on `Lesson.tsx`; in the prefetch use `null` for levelId unless the caller has it (see prefetch below).

> The `['module', m.id, 'lessons']` query in `Lessons.tsx` (uses `listLessons`) is **out of scope** — it is not in the market invalidation set and not part of the level/lesson reading path. Leave it unwrapped.

- [ ] **Step 1: Extend the prefetch test (write-through)**

```tsx
// add to usePrefetchLevelLessons.test.tsx
vi.mock('@/lib/offline/scope', () => ({ scopeFromMe: () => ({ childId: 'C1', market: 'GB' }) }));
vi.mock('@/lib/offline/contentStore', () => ({ upsertLesson: vi.fn(async () => {}) }));
vi.mock('@/lib/offline/useOfflineContent', () => ({
  cacheFirst: (opts: { fetch: () => unknown }) => opts.fetch, // identity: prefetch still calls fetch
}));
```
and assert the prefetched `queryFn` is produced via `cacheFirst` (i.e. `getLesson` still invoked twice as before — existing assertions stay green). Keep the existing 3 tests passing.

> The prefetch wrapper must read `me` from the queryClient to build `scope`. Update `usePrefetchLevelLessons` to accept the queryClient's `me` and pass each lesson's `level` if available; if `levelId` is unknown at prefetch time, pass `null`.

- [ ] **Step 2: Run to verify the new expectations fail** (prefetch not yet wrapped).

- [ ] **Step 3: Implement the prefetch write-through**

```tsx
// usePrefetchLevelLessons.ts — wrap the prefetch queryFn
import { scopeFromMe } from '@/lib/offline/scope';
import { cacheFirst } from '@/lib/offline/useOfflineContent';
import { getLesson, upsertLesson } from '@/lib/offline/contentStore';
import type { Me } from '@/api/auth';
// inside run():
const scope = scopeFromMe(queryClient.getQueryData<Me>(['me']));
for (const lesson of lessons) {
  void queryClient.prefetchQuery({
    queryKey: ['lesson', lesson.id],
    queryFn: cacheFirst({
      scope,
      fetch: () => contentApi.getLesson(lesson.id),
      read: (s) => getLesson(s, lesson.id),
      write: (s, data) => upsertLesson(s, data, null),
    }),
    staleTime: 60 * 60 * 1000,
  });
}
```

Then apply the page wraps (Lessons/Module/Level/Lesson) as shown above.

- [ ] **Step 4: Run the full content-page + prefetch suites**

Run: `cd frontend && npx vitest run src/hooks/__tests__/usePrefetchLevelLessons.test.tsx src/pages/child/__tests__` and confirm the Lesson/Level/Module page tests still pass (the wrap is transparent online: `cacheFirst` calls `fetch` which is the original `contentApi.*`). Run the FULL suite `npx vitest run` and confirm the failing set equals the known baseline (no NEW failures). tsc + lint clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/child/Lessons.tsx frontend/src/pages/child/Module.tsx frontend/src/pages/child/Level.tsx frontend/src/pages/child/Lesson.tsx frontend/src/hooks/usePrefetchLevelLessons.ts frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx
git commit -m "feat(offline): cache-first write-through for content queries + prefetch"
```

---

### Task 7: Native persist trim + clear-on-logout/region-switch

**Files:**
- Modify: `frontend/src/lib/queryPersistence.ts`
- Modify: `frontend/src/lib/__tests__/queryPersistence.test.ts`
- Modify: `frontend/src/components/child/ProfileMenu.tsx` (logout `onSettled` + RegionSwitcher area)
- Modify: `frontend/src/hooks/useMarkets.ts` (`useSwitchMarket` `onSuccess`)

This task has two deliverables: (a) the persist-allowlist trim, and (b) wiring
`clearForChild()` so a previous child's cached content is purged on logout and on
region/market switch (privacy/hygiene — scoping already prevents *read* leakage,
this is defense-in-depth + storage cleanup).

**Interfaces:**
- Consumes: `isOfflineDbAvailable` from `./offline/sqlite`; `clearForChild` + `scopeFromMe` (Tasks 2, 4); `Me` from `@/api/auth`.
- Produces: `shouldDehydrateQuery` excludes the content heads (`modules`, `module-levels`, `level-lessons`, `lesson`, `module`) when `isOfflineDbAvailable()` (native — SQLite owns them); keeps them on web. Plus `clearForChild(scope)` invoked on logout + region/market switch.

> Implementation: split the allowlist into `CONTENT_QUERY_KEYS` (the 5 content heads) and the rest. `shouldDehydrateQuery` returns false for a content head when `isOfflineDbAvailable()`.

- [ ] **Step 1: Add failing tests**

```ts
// add to queryPersistence.test.ts
vi.mock('../offline/sqlite', () => ({ isOfflineDbAvailable: vi.fn(() => false) }));
import { isOfflineDbAvailable } from '../offline/sqlite';
// ...
it('persists lesson queries on web (DB unavailable)', () => {
  vi.mocked(isOfflineDbAvailable).mockReturnValue(false);
  expect(shouldDehydrateQuery(successQuery(['lesson', 'L1']))).toBe(true);
});
it('drops content queries on native (SQLite owns them)', () => {
  vi.mocked(isOfflineDbAvailable).mockReturnValue(true);
  expect(shouldDehydrateQuery(successQuery(['lesson', 'L1']))).toBe(false);
  expect(shouldDehydrateQuery(successQuery(['progress']))).toBe(true); // non-content still persists
});
```
(`successQuery(key)` = a helper building a `{ state:{status:'success'}, queryKey:key }` cast `as unknown as Query`, matching the existing test file's style.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement**

```ts
// queryPersistence.ts
import { isOfflineDbAvailable } from './offline/sqlite';

const CONTENT_QUERY_KEYS: readonly string[] = ['modules', 'module-levels', 'level-lessons', 'lesson', 'module'];

export function shouldDehydrateQuery(query: Query): boolean {
  if (query.state.status !== 'success') return false;
  const head = query.queryKey[0];
  if (typeof head !== 'string' || !PERSISTED_QUERY_KEYS.includes(head)) return false;
  // On native, content lives in SQLite — keep it out of the localStorage blob.
  if (isOfflineDbAvailable() && CONTENT_QUERY_KEYS.includes(head)) return false;
  return true;
}
```
(Keep `PERSISTED_QUERY_KEYS` as-is so the union still covers web.)

- [ ] **Step 4: Run to verify it passes** — new tests + all existing `queryPersistence` tests green. tsc + lint clean.

- [ ] **Step 5: Wire `clearForChild` on logout + region/market switch**

In `ProfileMenu.tsx` logout mutation `onSettled` (currently only `qc.removeQueries({ queryKey: ['me'] })`), purge the offline cache first while `me` is still readable:

```tsx
import { scopeFromMe } from '@/lib/offline/scope';
import { clearForChild } from '@/lib/offline/contentStore';
import type { Me } from '@/api/auth';
// ...
const logout = useMutation({
  mutationFn: () => authApi.logout(),
  onSettled: async () => {
    const scope = scopeFromMe(qc.getQueryData<Me>(['me']));
    if (scope) await clearForChild(scope);   // no-op on web
    qc.removeQueries({ queryKey: ['me'] });
    navigate('/login', { replace: true });
  },
});
```

In `useMarkets.ts` `useSwitchMarket` `onSuccess` (and the `RegionSwitcher` switch `onSuccess`), clear the OLD scope's content before the invalidations refetch the new market — read `me` BEFORE it's invalidated:

```tsx
// useSwitchMarket onSuccess, before invalidating CONTENT_KEYS:
const prevScope = scopeFromMe(queryClient.getQueryData<Me>(['me']));
if (prevScope) await clearForChild(prevScope);   // no-op on web
// ...then the existing invalidateQueries calls
```

Add a focused test (mock `contentStore.clearForChild`): logout `onSettled` calls `clearForChild` with the derived scope then `removeQueries(['me'])`. (RegionSwitcher/market-switch clear can be covered by a single switch-path test.)

- [ ] **Step 6: Run** — clear-wiring test + the persist-trim tests green; full suite baseline; tsc + lint clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/queryPersistence.ts frontend/src/lib/__tests__/queryPersistence.test.ts frontend/src/components/child/ProfileMenu.tsx frontend/src/hooks/useMarkets.ts
git commit -m "feat(offline): persist trim on native + clearForChild on logout/region-switch"
```

---

### Task 8: Install plugin + native config + cap sync

**Files:**
- Modify: `frontend/package.json` (dependency — likely already added in Task 1; confirm)
- Modify: `frontend/capacitor.config.ts` (no plugin block needed for SQLite default; confirm build)
- Native: `npx cap sync`

- [ ] **Step 1:** Confirm `@capacitor-community/sqlite` is in `frontend/package.json` deps at a Capacitor-8-compatible version (`^6` line supports Capacitor 7+/8; verify `npm ls @capacitor-community/sqlite` resolves and peer-deps are satisfied for `@capacitor/core@^8`). If a peer conflict appears, pin the latest version whose peer range includes `@capacitor/core@^8`.
- [ ] **Step 2:** `cd frontend && npm run build` → succeeds (no web SQLite init path is added; web stays on localStorage).
- [ ] **Step 3:** `cd frontend && npx cap sync` → iOS + Android pick up the plugin. Confirm `Sync finished`.
- [ ] **Step 4:** `git status` — commit any tracked native changes from `cap sync` (e.g. `ios/App/Podfile`, `android/...` if tracked). Note in the commit body: **native rebuild (Xcode/Gradle) is an operator follow-up** to ship the plugin on device.
- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/capacitor.config.ts ios android
git commit -m "chore(offline): add @capacitor-community/sqlite + cap sync (native rebuild = operator follow-up)"
```

---

### Task 9: Figma mockups for the availability UX (controller + user gate)

> **Not an implementer-subagent task.** Per the standing Figma-first rule, the controller designs the three surfaces in the design-system Figma file (`h5xrUTiNDZqqhu4pvYprqc`) and shows them inline via the visualize widget for approval BEFORE Tasks 10–12.

- [ ] **Step 1:** Mock the **OfflineBadge** (a small "Available offline" pill/indicator on a level card), the **Downloaded view** (a list of saved levels with remove), and the **Download-this-level action** (button + progress state) — using the sky-blue brand tokens + Penny styling.
- [ ] **Step 2:** Present the mockups for approval. Iterate until approved.
- [ ] **Step 3:** Record the approved visual spec (component anatomy, tokens, copy) into this plan's Tasks 10–12 before dispatching their implementers.

---

### Task 10: OfflineBadge + availability hook

**Files:**
- Create: `frontend/src/hooks/useOfflineAvailability.ts` (reads `listAvailableOffline` for the active scope; native-only; returns `{ levelIds: Set<string>; lessonCount: number }`)
- Create: `frontend/src/components/child/OfflineBadge.tsx`
- Test: `frontend/src/components/child/__tests__/OfflineBadge.test.tsx` (+ `vitest-axe`)
- Mount: on the level card in `Module.tsx` (badge shown when `levelIds.has(level.id)`)

**Interfaces:**
- Consumes: `listAvailableOffline`, `scopeFromMe`, `isOfflineDbAvailable`.
- Produces: `useOfflineAvailability(): { levelIds: Set<string>; lessonCount: number }`; `<OfflineBadge />` (presentational, label "Available offline", a11y label, hidden when not native).

- [ ] **Step 1: Write failing tests** — badge renders the label + has no axe violations; hook returns the level-id set from a mocked `listAvailableOffline`; badge renders nothing when `isOfflineDbAvailable()` is false. (Use the approved Figma copy/markup from Task 9.)
- [ ] **Step 2: Run to verify fail.**
- [ ] **Step 3: Implement** the hook (a `useQuery` keyed `['offline-availability', scope?.childId, scope?.market]`, `enabled: isOfflineDbAvailable() && !!scope`, `queryFn` → `listAvailableOffline(scope!)`) and the badge (markup per Figma). Mount in `Module.tsx`.
- [ ] **Step 4: Run** — tests + axe green; full suite baseline; tsc + lint.
- [ ] **Step 5: Commit** `feat(offline): available-offline badge + availability hook`.

---

### Task 11: Downloaded-content view

**Files:**
- Create: `frontend/src/pages/child/Downloaded.tsx` (lists saved levels via `useOfflineAvailability`; each row → its level; a "remove" action calling a new `contentStore.removeLevel(scope, levelId)` that deletes that level's lessons + level-lessons row)
- Modify: `frontend/src/lib/offline/contentStore.ts` (+ `removeLevel`) and its test
- Add route + a nav entry (follow existing route/nav patterns); Test: page render + empty state + remove calls store (+ `vitest-axe`)

**Interfaces:**
- Produces: `removeLevel(scope, levelId): Promise<void>` (DELETE from `cached_lesson` WHERE level_id=? + `cached_level_lessons` WHERE level_id=?, scoped); `<Downloaded />` page.

- [ ] **Steps:** TDD `removeLevel` (test asserts both DELETEs, scoped) → implement → TDD the page (empty state when `levelIds` empty; lists levels; remove triggers `removeLevel` + invalidates `['offline-availability']`) → implement per Figma → route + nav → run (axe + baseline) → commit `feat(offline): downloaded-content view + removeLevel`.

---

### Task 12: "Download this level for offline" action

**Files:**
- Create: `frontend/src/components/child/DownloadLevelButton.tsx` (online-only; on click, fetch every lesson in the level via `contentApi.getLesson` and `upsertLesson(scope, lesson, levelId)`, showing progress; disabled offline + when already fully available)
- Mount: on `Level.tsx`
- Test: `__tests__/DownloadLevelButton.test.tsx` (+ `vitest-axe`)

**Interfaces:**
- Consumes: `useOnline`, `scopeFromMe`, `upsertLesson`, `useOfflineAvailability`, the level's `LessonSummary[]` (already loaded on `Level.tsx`).

- [ ] **Steps:** TDD — button hidden offline; click ingests all lessons (assert `upsertLesson` called per lesson) + shows progress + ends in "Available offline"; disabled when already available; no axe violations → implement per Figma → mount in `Level.tsx` → run (axe + baseline) → commit `feat(offline): download-this-level action`.

---

### Task 13: Full verification + ship + docs

**Files:**
- Modify: `docs/MASTER-BACKLOG.md` (mark Goal 4 Phase 3 shipped)

- [ ] **Step 1:** From `frontend/`: `npx tsc --noEmit` clean; `npm run lint` 0 errors; `npx vitest run` — confirm the failing set equals the known local-env baseline (no NEW failures); `npm run build` clean.
- [ ] **Step 2:** `npx cap sync` (re-sync the final web bundle into native).
- [ ] **Step 3:** Push to `main`; watch CI via `gh run view <id> --json status,conclusion,jobs` (NEVER `gh run watch | tail`); confirm all 6 jobs green (Backend may show `skipped`).
- [ ] **Step 4:** Vercel two-step: `vercel --prod --yes` (from `frontend/`) → `vercel alias set <hash>-investikid.vercel.app app.investikid.ai`; verify `curl -s -o /dev/null -w '%{http_code}' https://app.investikid.ai/` → 200.
- [ ] **Step 5:** Update `docs/MASTER-BACKLOG.md`: Phase 3 ✅ DONE with the commit range; remaining Goal 4 = none (Phase 3 was the last). Note native rebuild as operator follow-up. Commit `docs: mark Goal 4 Phase 3 shipped` + push.

---

## Notes for the executor

- **CI-safety discipline (learned this project):** verify frontend lint with `npm run lint` (= `eslint .`), never `eslint src/`; before any push, run the FULL `npx vitest run` and confirm the failing set equals the known baseline (~68 local-env URL-mismatch failures) — a NEW failure blocks. Stash+rerun to prove a failure is pre-existing.
- **Do not touch** `offlineMutations.ts` or web-persister behavior.
- **Native verification** (real device/emulator) is operator QA after the native build — unit tests cover the logic via mocked plugin; the on-device path is exercised post-rebuild.
