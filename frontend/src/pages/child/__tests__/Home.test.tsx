import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import Home from '../Home';

vi.mock('@/components/child/HomeHero', () => ({ default: () => null }));
vi.mock('@/api/collectables', () => ({
  useCollectables: () => ({
    data: {
      active: [{
        slug: 'home-feat', name: 'Home Featured', emoji: '👑', type: 'accessory',
        rarity: 'legendary', ends_at: '2099-01-01T00:00:00Z',
        goal: { type: 'streak_days', threshold: 7, current: 3 }, earned: false,
      }],
      owned: [],
    },
    isLoading: false,
  }),
}));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { level: 2, xp: 150, streak_count: 3, streak_freezes: 1, last_activity_date: '2026-06-11' } }),
}));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({
    data: { review_summary: { due_count: 2, next_due_at: null }, continue_learning: [], practise_again: [], something_new: [] },
  }),
}));
vi.mock('@/hooks/usePortfolio', () => ({
  usePortfolio: () => ({ data: { total_value: '125.00', currency_code: 'USD' } }),
}));
vi.mock('@/hooks/useAllBadges', () => ({
  useAllBadges: () => ({ data: [{ id: 'b1', name: 'First Step' }, { id: 'b2', name: 'Streak Star' }] }),
}));
vi.mock('@/hooks/useBadges', () => ({
  useBadges: () => ({ data: [{ id: 'b1', name: 'First Step', earned_at: '2026-06-01T00:00:00Z' }] }),
}));

function renderHome() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>
        <MemoryRouter>
          <Home />
        </MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

describe('Home composition (m3)', () => {
  it('renders sections in hierarchy order and no modules grid', () => {
    renderHome();
    expect(screen.getByRole('heading', { name: /your learning home/i })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: /your progress/i })).toBeInTheDocument(); // StatsCard
    expect(screen.getByRole('navigation', { name: /shortcuts/i })).toBeInTheDocument(); // QuickLinksRow
    expect(screen.queryByText(/your modules/i)).toBeNull(); // grid gone
    expect(screen.getByRole('link', { name: /browse all modules/i })).toBeInTheDocument();
  });

  it('derives badge counts as earned of total in the shortcuts row', () => {
    renderHome();
    expect(screen.getByRole('link', { name: /badges 1 of 2/i })).toBeInTheDocument();
  });

  it('shows the review shortcut when concepts are due', () => {
    renderHome();
    expect(screen.getByRole('link', { name: /2 to review/i })).toBeInTheDocument();
  });

  it('shows the featured-drop card above the arcade daily card when a drop is live', () => {
    renderHome();
    const featured = screen.getByText('Home Featured');
    expect(featured).toBeInTheDocument();
    // ArcadeDailyCard renders t('dailyCard.title') which resolves to 'MoneyWord' via the catalog mock.
    const arcade = screen.getByText(/MoneyWord/);
    // The featured card must appear before the arcade daily card in the DOM.
    expect(featured.compareDocumentPosition(arcade) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
