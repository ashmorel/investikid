// frontend/src/hooks/__tests__/useOfflineAvailability.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock BEFORE imports that use them
vi.mock('@/lib/offline/sqlite', () => ({
  isOfflineDbAvailable: vi.fn(() => true),
}));
vi.mock('@/lib/offline/contentStore', () => ({
  listAvailableOffline: vi.fn(async () => ({ levelIds: ['LV1', 'LV2'], lessonCount: 5 })),
}));

import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { listAvailableOffline } from '@/lib/offline/contentStore';
import { useOfflineAvailability } from '../useOfflineAvailability';

const mockIsAvailable = vi.mocked(isOfflineDbAvailable);
const mockList = vi.mocked(listAvailableOffline);

function wrapper(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsAvailable.mockReturnValue(true);
  mockList.mockResolvedValue({ levelIds: ['LV1', 'LV2'], lessonCount: 5 });
});

describe('useOfflineAvailability', () => {
  it('returns a Set built from listAvailableOffline level ids when native', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['me'], { id: 'C1', active_market_code: 'GB' });

    const { result } = renderHook(() => useOfflineAvailability(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.levelIds.size).toBe(2));
    expect(result.current.levelIds.has('LV1')).toBe(true);
    expect(result.current.levelIds.has('LV2')).toBe(true);
    expect(result.current.lessonCount).toBe(5);
  });

  it('returns empty Set + 0 when isOfflineDbAvailable() is false (query disabled)', async () => {
    mockIsAvailable.mockReturnValue(false);
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['me'], { id: 'C1', active_market_code: 'GB' });

    const { result } = renderHook(() => useOfflineAvailability(), { wrapper: wrapper(qc) });

    // query is disabled, stays loading=false idle
    await waitFor(() => expect(result.current.levelIds.size).toBe(0));
    expect(result.current.lessonCount).toBe(0);
    expect(mockList).not.toHaveBeenCalled();
  });

  it('returns empty Set + 0 when scope is null (no me in cache)', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // no ['me'] entry → scope null → query disabled

    const { result } = renderHook(() => useOfflineAvailability(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(result.current.levelIds.size).toBe(0));
    expect(result.current.lessonCount).toBe(0);
    expect(mockList).not.toHaveBeenCalled();
  });
});
