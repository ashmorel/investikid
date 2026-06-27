// frontend/src/hooks/__tests__/usePrefetchLevelLessons.test.tsx
import { renderHook } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

const prefetchQuery = vi.fn();
vi.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ prefetchQuery, getQueryData: vi.fn() }) }));
vi.mock('@/hooks/useOnline', () => ({ useOnline: vi.fn() }));
vi.mock('@/api/content', () => ({ contentApi: { getLesson: vi.fn(async () => ({})) } }));
vi.mock('@/lib/offline/scope', () => ({ scopeFromMe: () => ({ childId: 'C1', market: 'GB' }) }));
vi.mock('@/lib/offline/contentStore', () => ({ upsertLesson: vi.fn(async () => {}) }));
vi.mock('@/lib/offline/useOfflineContent', () => ({
  cacheFirst: (opts: { fetch: () => unknown }) => opts.fetch,
}));

import type { LessonSummary } from '@/api/content';
import { useOnline } from '@/hooks/useOnline';
import { usePrefetchLevelLessons } from '../usePrefetchLevelLessons';
const mockOnline = vi.mocked(useOnline);

const lessons = [{ id: 'a' }, { id: 'b' }] as unknown as LessonSummary[];

beforeEach(() => {
  prefetchQuery.mockClear();
  // run idle callbacks synchronously
  vi.stubGlobal('requestIdleCallback', (cb: () => void) => { cb(); return 1; });
  vi.stubGlobal('cancelIdleCallback', vi.fn());
});
afterEach(() => vi.unstubAllGlobals());

describe('usePrefetchLevelLessons', () => {
  it('prefetches each lesson when online', () => {
    mockOnline.mockReturnValue(true);
    renderHook(() => usePrefetchLevelLessons(lessons));
    expect(prefetchQuery).toHaveBeenCalledTimes(2);
    expect(prefetchQuery.mock.calls[0][0].queryKey).toEqual(['lesson', 'a']);
    expect(prefetchQuery.mock.calls[1][0].queryKey).toEqual(['lesson', 'b']);
  });

  it('does nothing when offline', () => {
    mockOnline.mockReturnValue(false);
    renderHook(() => usePrefetchLevelLessons(lessons));
    expect(prefetchQuery).not.toHaveBeenCalled();
  });

  it('does nothing for empty/null lessons', () => {
    mockOnline.mockReturnValue(true);
    renderHook(() => usePrefetchLevelLessons(null));
    expect(prefetchQuery).not.toHaveBeenCalled();
  });
});
