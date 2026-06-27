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

  describe('removeLevel', () => {
    it('deletes scoped rows from both cached_lesson and cached_level_lessons', async () => {
      await store.removeLevel(scope, 'LV1');
      expect(run).toHaveBeenCalledTimes(2);
      const [sql1, v1] = run.mock.calls[0] as unknown as [string, unknown[]];
      const [sql2, v2] = run.mock.calls[1] as unknown as [string, unknown[]];
      expect(sql1).toContain('DELETE FROM cached_lesson');
      expect(v1).toEqual(['C1', 'GB', 'LV1']);
      expect(sql2).toContain('DELETE FROM cached_level_lessons');
      expect(v2).toEqual(['C1', 'GB', 'LV1']);
    });

    it('no-ops when DB is unavailable', async () => {
      vi.mocked(isOfflineDbAvailable).mockReturnValueOnce(false);
      await store.removeLevel(scope, 'LV1');
      expect(run).not.toHaveBeenCalled();
    });

    it('swallows DB errors', async () => {
      run.mockRejectedValueOnce(new Error('disk'));
      await expect(store.removeLevel(scope, 'LV1')).resolves.toBeUndefined();
    });
  });

  describe('listDownloadedLevels', () => {
    it('returns levelId, title from module-levels cache, and lessonCount', async () => {
      // First query: level rows
      query.mockResolvedValueOnce({
        values: [
          { level_id: 'LV1', n: 3 },
          { level_id: 'LV2', n: 1 },
        ],
      });
      // Second query: module_levels payload_json rows
      query.mockResolvedValueOnce({
        values: [
          { payload_json: JSON.stringify([{ id: 'LV1', title: 'Intro to Stocks' }, { id: 'LV2', title: 'Risk Basics' }]) },
        ],
      });
      const result = await store.listDownloadedLevels(scope, 1000);
      expect(result).toEqual([
        { levelId: 'LV1', title: 'Intro to Stocks', lessonCount: 3 },
        { levelId: 'LV2', title: 'Risk Basics', lessonCount: 1 },
      ]);
    });

    it('falls back to levelId string when title is not in cache', async () => {
      query.mockResolvedValueOnce({ values: [{ level_id: 'LV99', n: 2 }] });
      query.mockResolvedValueOnce({ values: [] }); // no module-levels rows
      const result = await store.listDownloadedLevels(scope, 1000);
      expect(result).toEqual([{ levelId: 'LV99', title: 'LV99', lessonCount: 2 }]);
    });

    it('returns [] when no fresh lessons', async () => {
      query.mockResolvedValueOnce({ values: [] });
      const result = await store.listDownloadedLevels(scope, 1000);
      expect(result).toEqual([]);
    });

    it('returns [] when unavailable', async () => {
      vi.mocked(isOfflineDbAvailable).mockReturnValueOnce(false);
      expect(await store.listDownloadedLevels(scope, 1000)).toEqual([]);
    });

    it('returns [] on DB error', async () => {
      query.mockRejectedValueOnce(new Error('disk'));
      expect(await store.listDownloadedLevels(scope, 1000)).toEqual([]);
    });
  });

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
        const [sql, values] = call as unknown as [string, unknown[]];
        expect(values).toEqual(['C1', 'GB']);
        expect(sql).toContain('DELETE FROM cached_');
      }
    });
  });
});
