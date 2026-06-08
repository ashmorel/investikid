import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import Home from '../Home';

// The highlight must follow the next-lesson resolver (m2), NOT the recommendations (m1).
vi.mock('@/hooks/useNextLesson', () => ({
  useNextLesson: () => ({
    mode: 'continue', moduleId: 'm2', levelId: 'l1', lessonId: 'q1',
    moduleTitle: 'Budgeting', moduleIcon: '💰', lessonLabel: 'Needs vs Wants',
    to: '/lessons/m2/l1/q1', isLoading: false,
  }),
}));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({
    data: { review_summary: { due_count: 0 }, continue_learning: [{ module_id: 'm1' }], something_new: [] },
  }),
}));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { level: 1, xp: 0, streak_count: 0, last_activity_date: null } }),
}));
vi.mock('@/hooks/useAllBadges', () => ({ useAllBadges: () => ({ data: [] }) }));
vi.mock('@/hooks/useBadges', () => ({ useBadges: () => ({ data: [] }) }));
// Stub the heavy child components so the test focuses on the module grid.
vi.mock('@/components/child/HomeHero', () => ({ default: () => null }));
vi.mock('@/components/child/StatsBar', () => ({ StatsBar: () => null }));
vi.mock('@/components/child/LevelProgressCard', () => ({ LevelProgressCard: () => null }));
vi.mock('@/components/child/AchievementsStrip', () => ({ AchievementsStrip: () => null }));
vi.mock('@/components/child/ReviewBanner', () => ({ ReviewBanner: () => null }));
vi.mock('@/api/content', () => ({
  contentApi: {
    listModules: () => Promise.resolve([
      { id: 'm1', order_index: 0, topic: 'stocks', icon: '📈', title: 'Stocks', locked: false },
      { id: 'm2', order_index: 1, topic: 'budgeting', icon: '💰', title: 'Budgeting', locked: false },
    ]),
  },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><PremiumPaywallProvider><MemoryRouter>{ui}</MemoryRouter></PremiumPaywallProvider></QueryClientProvider>;
}

describe('Home module grid highlight', () => {
  it('marks the next-lesson module (m2) as "Next", not the recommendations module (m1)', async () => {
    render(wrap(<Home />));
    const budgeting = (await screen.findByText('Budgeting')).closest('a')!;
    expect(budgeting).toHaveTextContent('Next');
    const stocks = screen.getByText('Stocks').closest('a')!;
    expect(stocks).not.toHaveTextContent('Next');
  });
});
