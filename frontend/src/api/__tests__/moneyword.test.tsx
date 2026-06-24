import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../client', () => ({
  apiFetch: vi.fn().mockResolvedValue({
    length: 5, max_guesses: 6, guesses: [], completed: false,
    solved: false, definition: null, already_played: false,
  }),
}));

import { useMoneyWordToday } from '../moneyword';

describe('useMoneyWordToday', () => {
  it('keys the daily query by UTC day so it resets at the 00:00 UTC boundary', async () => {
    const qc = new QueryClient();
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    );
    renderHook(() => useMoneyWordToday(), { wrapper });

    await waitFor(() => expect(qc.getQueryCache().getAll().length).toBeGreaterThan(0));

    const key = qc.getQueryCache().getAll()[0].queryKey;
    const utcDay = new Date().toISOString().slice(0, 10);
    // The UTC day is the last segment — a new day yields a new key, so a cached
    // "completed" board can never leak into the next day.
    expect(key).toEqual(['arcade', 'moneyword', 'today', utcDay]);
  });
});
