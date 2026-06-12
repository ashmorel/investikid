import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';

const ME = {
  id: 'u1', email: 'k@x.com', username: 'kid42', dob: '2012-01-01',
  country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
  parent_email: null, created_at: '2026-04-29T00:00:00Z',
};

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method ?? 'GET').toUpperCase();
    const key = `${method} ${url}`;
    for (const [path, body] of Object.entries(routeMap)) {
      if (key === path || url === path) {
        return new Response(JSON.stringify(body), { status: 200 });
      }
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
}

function renderAt(path: string, ui: React.ReactNode, routePattern: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={routePattern} element={<>{ui}</>} />
          </Routes>
        </MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

// Mock Stats hooks once for the whole file
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
      { username: 'kid42', country_code: 'US', xp_this_week: 100 },
    ],
    isLoading: false,
  }),
}));
let mockAgeTier: 'explorer' | 'investor' = 'explorer';
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({ data: { username: 'kid42', age_tier: mockAgeTier } }),
}));
vi.mock('canvas-confetti', () => ({ default: vi.fn() }));
vi.mock('@/components/child/HomeHero', () => ({ default: () => <p>HomeHero</p> }));
vi.mock('@/api/ai', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/ai')>();
  return {
    ...actual,
    useRecommendations: () => ({
      data: { continue_learning: [], something_new: [], practise_again: [], review_summary: { due_count: 0, next_due_at: null } },
      isLoading: false,
    }),
  };
});

describe('a11y: child core surfaces', () => {
  it('Home has no axe violations', async () => {
    mockJsonRoute({
      '/users/me': ME,
      '/users/me/progress': { xp: 320, level: 4, streak_count: 5, last_activity_date: '2026-05-02' },
    });
    const { default: Home } = await import('@/pages/child/Home');
    const { container } = renderAt('/home', <Home />, '/home');
    await waitFor(() => expect(screen.getByText(/HomeHero/i)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole('group', { name: /your progress/i })).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Home (investor tier) has no axe violations and no emoji', async () => {
    mockAgeTier = 'investor';
    try {
      mockJsonRoute({
        '/users/me': ME,
        '/users/me/progress': { xp: 320, level: 4, streak_count: 5, last_activity_date: '2026-05-02' },
      });
      const { default: Home } = await import('@/pages/child/Home');
      const { container } = renderAt('/home', <Home />, '/home');
      await waitFor(() => expect(screen.getByRole('group', { name: /your progress/i })).toBeInTheDocument());
      expect(container.textContent).not.toMatch(/[⭐🔥🛡📊🔁🏅]/u);
      expect(await axe(container)).toHaveNoViolations();
    } finally {
      mockAgeTier = 'explorer';
    }
  });

  it('Lessons has no axe violations', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false },
        { id: 'mod-2', topic: 'savings', title: 'M2', country_codes: [], is_premium: false, order_index: 1, locked: false },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 't', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'card', title: 't', xp_reward: 10, order_index: 1, completed: false },
      ],
      '/modules/mod-2/lessons': [
        { id: 'L3', type: 'card', title: 't', xp_reward: 10, order_index: 0, completed: false },
      ],
    });
    const { default: Lessons } = await import('@/pages/child/Lessons');
    const { container } = renderAt('/lessons', <Lessons />, '/lessons');
    await waitFor(() => expect(screen.getByText('M1')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Module has no axe violations', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, locked: false },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'quiz', title: 'Second', xp_reward: 25, order_index: 1, completed: false },
      ],
    });
    const { default: Module } = await import('@/pages/child/Module');
    const { container } = renderAt('/lessons/mod-1', <Module />, '/lessons/:moduleId');
    await waitFor(() => expect(screen.getByRole('heading', { name: /Stocks 101/i })).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Lesson (card type) has no axe violations', async () => {
    mockJsonRoute({
      'GET /lessons/L1': {
        id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
        completed: false, locked: false,
        content_json: { title: 'CardT', body: 'CardB' },
      },
      'GET /modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
      ],
      'GET /modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, locked: false },
      ],
    });
    const { default: Lesson } = await import('@/pages/child/Lesson');
    const { container } = renderAt('/lessons/mod-1/L1', <Lesson />, '/lessons/:moduleId/:lessonId');
    await waitFor(() => expect(screen.getByRole('heading', { name: /CardT/i })).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Stats has no axe violations', async () => {
    const { default: Stats } = await import('@/pages/child/Stats');
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <PremiumPaywallProvider>
          <MemoryRouter><Stats /></MemoryRouter>
        </PremiumPaywallProvider>
      </QueryClientProvider>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
