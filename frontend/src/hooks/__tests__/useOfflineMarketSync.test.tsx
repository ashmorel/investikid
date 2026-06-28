// frontend/src/hooks/__tests__/useOfflineMarketSync.test.tsx
import { renderHook, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider, onlineManager } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock BEFORE importing modules that use them
vi.mock('@/lib/offline/marketSync', () => ({
  syncMarket: vi.fn(() => Promise.resolve()),
}));
vi.mock('@/lib/offline/sqlite', () => ({
  isOfflineDbAvailable: vi.fn(() => true),
}));

import { syncMarket } from '@/lib/offline/marketSync';
import { isOfflineDbAvailable } from '@/lib/offline/sqlite';
import { useOfflineMarketSync } from '../useOfflineMarketSync';

const mockSync = vi.mocked(syncMarket);
const mockIsAvailable = vi.mocked(isOfflineDbAvailable);

const ME = { id: 'C1', active_market_code: 'GB', content_region: 'GB' };

function wrapper(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

function makeQc(me?: typeof ME | null) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (me !== undefined) qc.setQueryData(['me'], me);
  return qc;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockIsAvailable.mockReturnValue(true);
  onlineManager.setOnline(true);
});

describe('useOfflineMarketSync', () => {
  it('calls syncMarket once when native + online + scope present', async () => {
    const qc = makeQc(ME);
    renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(1));
    expect(mockSync).toHaveBeenCalledWith({ childId: 'C1', market: 'GB' });
  });

  it('does NOT call syncMarket on web (isOfflineDbAvailable false)', async () => {
    mockIsAvailable.mockReturnValue(false);
    const qc = makeQc(ME);
    renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    // Give effect time to run if it were going to
    await new Promise((r) => setTimeout(r, 50));
    expect(mockSync).not.toHaveBeenCalled();
  });

  it('does NOT call syncMarket when offline', async () => {
    onlineManager.setOnline(false);
    const qc = makeQc(ME);
    renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockSync).not.toHaveBeenCalled();
  });

  it('does NOT call syncMarket when scope is null (no me)', async () => {
    const qc = makeQc(null);
    renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await new Promise((r) => setTimeout(r, 50));
    expect(mockSync).not.toHaveBeenCalled();
  });

  it('calls syncMarket only once on re-render with the same scope', async () => {
    const qc = makeQc(ME);
    const { rerender } = renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(1));

    rerender();
    rerender();

    await new Promise((r) => setTimeout(r, 50));
    expect(mockSync).toHaveBeenCalledTimes(1);
  });

  it('calls syncMarket again when scope changes (market switch)', async () => {
    const ME2 = { ...ME, active_market_code: 'US', content_region: 'US' };
    const qc = makeQc(ME);
    const { rerender } = renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(1));
    expect(mockSync).toHaveBeenCalledWith({ childId: 'C1', market: 'GB' });

    // Switch market
    qc.setQueryData(['me'], ME2);
    rerender();

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(2));
    expect(mockSync).toHaveBeenCalledWith({ childId: 'C1', market: 'US' });
  });

  it('calls syncMarket again when childId changes', async () => {
    const ME2 = { ...ME, id: 'C2' };
    const qc = makeQc(ME);
    const { rerender } = renderHook(() => useOfflineMarketSync(), { wrapper: wrapper(qc) });

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(1));

    qc.setQueryData(['me'], ME2);
    rerender();

    await waitFor(() => expect(mockSync).toHaveBeenCalledTimes(2));
    expect(mockSync).toHaveBeenLastCalledWith({ childId: 'C2', market: 'GB' });
  });
});
