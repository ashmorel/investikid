import { CapacitorSQLite, SQLiteConnection, type SQLiteDBConnection } from '@capacitor-community/sqlite';
import { isNativeApp } from '@/lib/platform';

/** Fallback-read staleness window; matches PERSIST_MAX_AGE. */
export const OFFLINE_MAX_AGE = 24 * 60 * 60 * 1000;

const DB_NAME = 'investikid';
const DB_VERSION = 2;

/** Schema v2. All content tables are scoped by (child_id, market). */
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
CREATE TABLE IF NOT EXISTS sync_meta (
  child_id TEXT NOT NULL, market TEXT NOT NULL, last_sync TEXT NOT NULL,
  PRIMARY KEY (child_id, market)
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
