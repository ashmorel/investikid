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

export async function removeLevel(scope: CacheScope, levelId: string): Promise<void> {
  if (!isOfflineDbAvailable()) return;
  try {
    const db = await getDb();
    if (!db) return;
    await db.run(
      `DELETE FROM cached_lesson WHERE child_id=? AND market=? AND level_id=?`,
      [scope.childId, scope.market, levelId],
    );
    await db.run(
      `DELETE FROM cached_level_lessons WHERE child_id=? AND market=? AND level_id=?`,
      [scope.childId, scope.market, levelId],
    );
  } catch {
    /* best-effort */
  }
}

export type DownloadedLevel = { levelId: string; title: string; lessonCount: number };

export async function listDownloadedLevels(
  scope: CacheScope,
  now: number = Date.now(),
): Promise<DownloadedLevel[]> {
  if (!isOfflineDbAvailable()) return [];
  try {
    const db = await getDb();
    if (!db) return [];
    const minTs = now - OFFLINE_MAX_AGE;
    // Get fresh level_id + lesson count per level
    const rows = await db.query(
      `SELECT level_id, COUNT(*) AS n FROM cached_lesson
       WHERE child_id=? AND market=? AND level_id IS NOT NULL AND cached_at>?
       GROUP BY level_id`,
      [scope.childId, scope.market, minTs],
    );
    if (!rows.values?.length) return [];

    // Build levelId→title map from cached_module_levels rows
    const levelRows = await db.query(
      `SELECT payload_json FROM cached_module_levels WHERE child_id=? AND market=?`,
      [scope.childId, scope.market],
    );
    const titleMap = new Map<string, string>();
    for (const row of (levelRows.values ?? []) as { payload_json: string }[]) {
      try {
        const levels = JSON.parse(row.payload_json) as LevelOut[];
        for (const lv of levels) {
          titleMap.set(lv.id, lv.title);
        }
      } catch {
        /* skip malformed row */
      }
    }

    return (rows.values as { level_id: string; n: number }[]).map((r) => ({
      levelId: r.level_id,
      title: titleMap.get(r.level_id) ?? r.level_id,
      lessonCount: Number(r.n),
    }));
  } catch {
    return [];
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
