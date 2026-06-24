import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useAllBadges } from '@/hooks/useAllBadges';
import { useBadges } from '@/hooks/useBadges';
import { useChallenges } from '@/hooks/useChallenges';
import { useLeaderboard } from '@/hooks/useLeaderboard';

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('useAllBadges', () => {
  it('fetches from GET /badges with staleTime Infinity', async () => {
    const body = [{ id: '1', name: 'X', description: '', icon_url: '', condition_type: 'lesson_count', condition_value: 1, earned_at: null }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useAllBadges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});

describe('useBadges', () => {
  it('fetches from GET /users/me/badges', async () => {
    const body = [{ id: '1', name: 'X', description: '', icon_url: '', earned_at: '2026-01-01T00:00:00Z' }];
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { result } = renderHook(() => useBadges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(body);
  });
});

describe('useChallenges', () => {
  it('fetches from GET /challenges', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useChallenges(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });
});

describe('useLeaderboard', () => {
  it('fetches from GET /leaderboard with scope + metric', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }),
    );
    const { result } = renderHook(() => useLeaderboard('market', 'xp'), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual([]);
  });
});
