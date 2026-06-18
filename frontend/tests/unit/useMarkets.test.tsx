import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../src/api/market', () => ({
  marketApi: {
    list: vi.fn().mockResolvedValue([{ code: 'GB', name: 'United Kingdom', currency_code: 'GBP', has_content: true, enrolled: true, is_selected: true }]),
    progress: vi.fn(),
    switch: vi.fn().mockResolvedValue({ active_market_code: 'US' }),
  },
}));

import { marketApi } from '../../src/api/market';
import { useSwitchMarket } from '../../src/hooks/useMarkets';

function wrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

describe('useSwitchMarket', () => {
  it('posts the code and invalidates content queries', async () => {
    const qc = new QueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useSwitchMarket(), { wrapper: wrapper(qc) });
    await act(async () => { await result.current.mutateAsync('US'); });
    expect(marketApi.switch).toHaveBeenCalledWith('US');
    const invalidated = spy.mock.calls.map((c) => (c[0] as { queryKey: string[] }).queryKey[0]);
    for (const k of ['me', 'modules', 'recommendations', 'next-lesson']) {
      expect(invalidated).toContain(k);
    }
  });
});
