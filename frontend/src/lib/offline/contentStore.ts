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
