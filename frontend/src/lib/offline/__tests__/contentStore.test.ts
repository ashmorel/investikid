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
    const [sql, values] = run.mock.calls[0] as unknown as [string, unknown[]];
    expect(sql).toContain('INTO cached_lesson');
    expect(sql).toContain('ON CONFLICT');
    expect(values).toEqual(['C1', 'GB', 'L1', 'LV1', JSON.stringify(lesson), 1000]);
  });

  it('getLesson returns the parsed payload for a fresh row', async () => {
    query.mockResolvedValueOnce({ values: [{ payload_json: JSON.stringify({ id: 'L1' }), cached_at: 1000 }] });
    const out = await store.getLesson(scope, 'L1', 1000);
    expect(out).toEqual({ id: 'L1' });
    const [sql, values] = query.mock.calls[0] as unknown as [string, unknown[]];
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
    const [, values] = run.mock.calls[0] as unknown as [string, unknown[]];
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
