import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import type { ReactNode } from 'react';

// Mock all data hooks
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({
    data: { xp: 150, level: 2, streak_count: 3, last_activity_date: '2026-05-08' },
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useAllBadges', () => ({
  useAllBadges: () => ({
    data: [
      { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useBadges', () => ({
  useBadges: () => ({
    data: [
      { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', earned_at: '2026-05-01T10:00:00Z' },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useChallenges', () => ({
  useChallenges: () => ({
    data: [
      { id: 'c1', title: 'Weekly Learner', description: 'Complete 3 lessons', type: 'lessons_completed', target_value: 3, xp_reward: 50, starts_at: '', ends_at: '', is_premium: false, progress: 1, completed_at: null },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useLeaderboard', () => ({
  useLeaderboard: () => ({
    data: [
      { username: 'testuser', country_code: 'GB', xp_this_week: 100 },
    ],
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({
    data: { username: 'testuser' },
  }),
}));

beforeEach(() => vi.restoreAllMocks());

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Stats page', () => {
  it('renders page title', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /your stats/i })).toBeInTheDocument();
  });

  it('renders XP summary section', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText(/Level 2/)).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('renders badges section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /badges/i })).toBeInTheDocument();
  });

  it('renders challenges section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /weekly challenges/i })).toBeInTheDocument();
  });

  it('renders leaderboard section heading', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByRole('heading', { name: /weekly leaderboard/i })).toBeInTheDocument();
  });

  it('renders challenge data', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText('Weekly Learner')).toBeInTheDocument();
  });

  it('renders leaderboard with current user highlighted', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    render(<Stats />, { wrapper });
    expect(screen.getByText('You')).toBeInTheDocument();
  });
});
