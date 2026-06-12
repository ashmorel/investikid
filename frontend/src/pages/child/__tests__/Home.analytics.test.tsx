import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PremiumPaywallProvider, usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import Home from '../Home';

vi.mock('@/lib/analytics', () => ({
  track: vi.fn(),
  trackOncePerSession: vi.fn(),
}));
vi.mock('@/components/child/HomeHero', () => ({ default: () => null }));
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({ data: { level: 2, xp: 150, streak_count: 3, streak_freezes: 0, last_activity_date: '2026-06-11' } }),
}));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({
    data: { review_summary: { due_count: 2, next_due_at: null }, continue_learning: [], practise_again: [], something_new: [] },
  }),
}));
vi.mock('@/hooks/usePortfolio', () => ({
  usePortfolio: () => ({ data: { total_value: '125.00', currency_code: 'USD' } }),
}));
vi.mock('@/hooks/useAllBadges', () => ({ useAllBadges: () => ({ data: [{ id: 'b1' }] }) }));
vi.mock('@/hooks/useBadges', () => ({ useBadges: () => ({ data: [] }) }));

import { track, trackOncePerSession } from '@/lib/analytics';

function renderHome(ui?: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>
        <MemoryRouter>{ui ?? <Home />}</MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.clearAllMocks());

describe('Home analytics wiring (m4)', () => {
  it('fires home_view once per session on mount', () => {
    renderHome();
    expect(trackOncePerSession).toHaveBeenCalledWith('home_view');
  });

  it('fires quicklink_tap with the chip surface', () => {
    renderHome();
    fireEvent.click(screen.getByRole('link', { name: /2 to review/i }));
    expect(track).toHaveBeenCalledWith('quicklink_tap', { surface: 'review' });
  });

  it('fires paywall_view when the paywall opens', () => {
    function Opener() {
      const { open } = usePremiumPaywall();
      return (
        <button type="button" onClick={() => open({ kind: 'module', label: 'Stocks' })}>
          open paywall
        </button>
      );
    }
    renderHome(<Opener />);
    fireEvent.click(screen.getByRole('button', { name: /open paywall/i }));
    expect(track).toHaveBeenCalledWith('paywall_view', { surface: 'module' });
  });
});
