// frontend/src/lib/offline/__tests__/marketSync.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { CacheScope } from '../scope';
import type { OfflineBundle } from '@/api/content';
import type { LessonOut, LevelOut, ModuleOut, LessonSummary } from '@/api/content';

// --- mock @/lib/offline/sqlite ---
vi.mock('@/lib/offline/sqlite', () => ({
  isOfflineDbAvailable: vi.fn(() => true),
}));

// --- mock contentStore functions ---
vi.mock('../contentStore', () => ({
  getLastSync: vi.fn(async () => null),
  setLastSync: vi.fn(async () => undefined),
  reconcileIds: vi.fn(async () => undefined),
  upsertModules: vi.fn(async () => undefined),
  upsertModuleLevels: vi.fn(async () => undefined),
  upsertLevelLessons: vi.fn(async () => undefined),
  upsertLesson: vi.fn(async () => undefined),
}));

// --- mock @/api/content ---
vi.mock('@/api/content', () => ({
  getOfflineBundle: vi.fn(async () => undefined),
}));

import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import * as contentStore from '../contentStore';
import * as contentApi from '@/api/content';
import { syncMarket } from '../marketSync';

// -----------------------------------------------------------------------
// Fixture data
// -----------------------------------------------------------------------
const scope: CacheScope = { childId: 'C1', market: 'GB' };

const module1 = { id: 'MOD1' } as unknown as ModuleOut;

const level1 = { id: 'LV1' } as unknown as LevelOut;
const level2 = { id: 'LV2' } as unknown as LevelOut;

const lessonSummary1: LessonSummary = {
  id: 'LS1', type: 'card', title: 'Lesson 1', xp_reward: 10, order_index: 0, completed: false,
};
const lessonSummary2: LessonSummary = {
  id: 'LS2', type: 'quiz', title: 'Lesson 2', xp_reward: 20, order_index: 1, completed: false,
};

const lesson1: LessonOut = {
  id: 'LS1', module_id: 'MOD1', type: 'card',
  content_json: {}, xp_reward: 10, order_index: 0, completed: false, locked: false,
};
const lesson2: LessonOut = {
  id: 'LS2', module_id: 'MOD1', type: 'quiz',
  content_json: {}, xp_reward: 20, order_index: 1, completed: false, locked: false,
};
// lesson3 is NOT in any level_lessons entry
const lesson3: LessonOut = {
  id: 'LS3', module_id: 'MOD1', type: 'card',
  content_json: {}, xp_reward: 5, order_index: 2, completed: false, locked: false,
};

const SERVER_TIME = '2026-06-28T12:00:00.000Z';
const SERVER_TIME_2 = '2026-06-28T13:00:00.000Z';
const SINCE_CURSOR = '2026-06-28T10:00:00.000Z';

function makeBundle(overrides: Partial<OfflineBundle> = {}): OfflineBundle {
  return {
    market: 'GB',
    server_time: SERVER_TIME,
    modules: [module1],
    module_levels: { MOD1: [level1, level2] },
    level_lessons: { LV1: [lessonSummary1], LV2: [lessonSummary2] },
    lessons: [lesson1, lesson2],
    current_ids: { modules: ['MOD1'], levels: ['LV1', 'LV2'], lessons: ['LS1', 'LS2'] },
    ...overrides,
  };
}

beforeEach(() => vi.clearAllMocks());

// -----------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------
describe('syncMarket', () => {
  describe('first sync (getLastSync → null)', () => {
    it('calls getOfflineBundle(null) on first sync', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(makeBundle());

      await syncMarket(scope);

      expect(contentApi.getOfflineBundle).toHaveBeenCalledTimes(1);
      expect(contentApi.getOfflineBundle).toHaveBeenCalledWith(null);
    });

    it('upserts modules', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.upsertModules).toHaveBeenCalledWith(scope, bundle.modules);
    });

    it('upserts each module_levels entry', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.upsertModuleLevels).toHaveBeenCalledWith(scope, 'MOD1', [level1, level2]);
    });

    it('upserts each level_lessons entry', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.upsertLevelLessons).toHaveBeenCalledWith(scope, 'LV1', [lessonSummary1]);
      expect(contentStore.upsertLevelLessons).toHaveBeenCalledWith(scope, 'LV2', [lessonSummary2]);
    });

    it('upserts each lesson with the correct levelId from the map', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      // LS1 is in LV1, LS2 is in LV2
      expect(contentStore.upsertLesson).toHaveBeenCalledWith(scope, lesson1, 'LV1');
      expect(contentStore.upsertLesson).toHaveBeenCalledWith(scope, lesson2, 'LV2');
    });

    it('calls reconcileIds with current_ids', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.reconcileIds).toHaveBeenCalledWith(scope, bundle.current_ids);
    });

    it('calls setLastSync with server_time', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      const bundle = makeBundle();
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.setLastSync).toHaveBeenCalledWith(scope, SERVER_TIME);
    });

    it('reconcileIds is called before setLastSync', async () => {
      const order: string[] = [];
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(makeBundle());
      vi.mocked(contentStore.reconcileIds).mockImplementation(async () => { order.push('reconcile'); });
      vi.mocked(contentStore.setLastSync).mockImplementation(async () => { order.push('setLastSync'); });

      await syncMarket(scope);

      expect(order).toEqual(['reconcile', 'setLastSync']);
    });
  });

  describe('second sync (getLastSync → cursor)', () => {
    it('calls getOfflineBundle with the stored cursor', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(SINCE_CURSOR);
      const bundle = makeBundle({ server_time: SERVER_TIME_2, lessons: [lesson2] });
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentApi.getOfflineBundle).toHaveBeenCalledWith(SINCE_CURSOR);
    });

    it('applies delta lessons and advances the cursor', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(SINCE_CURSOR);
      const bundle = makeBundle({ server_time: SERVER_TIME_2, lessons: [lesson2] });
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.upsertLesson).toHaveBeenCalledWith(scope, lesson2, 'LV2');
      expect(contentStore.setLastSync).toHaveBeenCalledWith(scope, SERVER_TIME_2);
    });
  });

  describe('error handling', () => {
    it('does not throw when getOfflineBundle throws', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockRejectedValueOnce(new Error('network'));

      await expect(syncMarket(scope)).resolves.toBeUndefined();
    });

    it('does NOT call reconcileIds when getOfflineBundle throws', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockRejectedValueOnce(new Error('network'));

      await syncMarket(scope);

      expect(contentStore.reconcileIds).not.toHaveBeenCalled();
    });

    it('does NOT call setLastSync when getOfflineBundle throws', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockRejectedValueOnce(new Error('network'));

      await syncMarket(scope);

      expect(contentStore.setLastSync).not.toHaveBeenCalled();
    });

    it('does NOT call reconcileIds when an upsert throws', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(makeBundle());
      vi.mocked(contentStore.upsertModules).mockRejectedValueOnce(new Error('disk'));

      await syncMarket(scope);

      expect(contentStore.reconcileIds).not.toHaveBeenCalled();
      expect(contentStore.setLastSync).not.toHaveBeenCalled();
    });

    it('does not throw when any store fn throws', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(makeBundle());
      vi.mocked(contentStore.upsertModules).mockRejectedValueOnce(new Error('disk'));

      await expect(syncMarket(scope)).resolves.toBeUndefined();
    });
  });

  describe('no-op when offline DB unavailable', () => {
    it('returns immediately without calling getOfflineBundle', async () => {
      vi.mocked(isOfflineDbAvailable).mockReturnValueOnce(false);

      await syncMarket(scope);

      expect(contentApi.getOfflineBundle).not.toHaveBeenCalled();
      expect(contentStore.getLastSync).not.toHaveBeenCalled();
      expect(contentStore.upsertModules).not.toHaveBeenCalled();
      expect(contentStore.reconcileIds).not.toHaveBeenCalled();
      expect(contentStore.setLastSync).not.toHaveBeenCalled();
    });
  });

  describe('lesson with unknown levelId', () => {
    it('calls upsertLesson with null when the lesson is not in any level_lessons list', async () => {
      vi.mocked(contentStore.getLastSync).mockResolvedValueOnce(null);
      // lesson3 (LS3) is in `lessons` but not in any level_lessons value
      const bundle = makeBundle({ lessons: [lesson1, lesson3] });
      vi.mocked(contentApi.getOfflineBundle).mockResolvedValueOnce(bundle);

      await syncMarket(scope);

      expect(contentStore.upsertLesson).toHaveBeenCalledWith(scope, lesson1, 'LV1');
      expect(contentStore.upsertLesson).toHaveBeenCalledWith(scope, lesson3, null);
    });
  });
});
