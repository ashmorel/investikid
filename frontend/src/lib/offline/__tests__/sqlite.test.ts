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
    const schemaSql = String((fakeDb.execute.mock.calls as unknown as string[][])[0][0]);
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
