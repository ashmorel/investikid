import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import Home from '@/pages/child/Home';

vi.mock('@/components/child/HomeHero', () => ({ default: () => null }));

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url === path) return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response('not mocked: ' + url, { status: 500 });
  });
}

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

const EMPTY_RECS = {
  continue_learning: [],
  practise_again: [],
  something_new: [],
  review_summary: { due_count: 0, next_due_at: null },
};

beforeEach(() => vi.restoreAllMocks());

describe('Home', () => {
  it('shows the browse-all link and no inline modules grid (B1: stats live in the hero)', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 320, level: 4, streak_count: 5, streak_freezes: 0, last_activity_date: '2026-05-02' },
      '/recommendations': EMPTY_RECS,
    });
    renderHome();
    // B1 focused Home: the standalone StatsCard ("your progress") is gone — the
    // daily goal + streak now live in HomeHero (mocked null here). Structure stays.
    expect(await screen.findByRole('link', { name: /browse all modules/i })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: /your progress/i })).toBeNull();
    expect(screen.queryByText(/Your modules/i)).toBeNull();
  });

  it('shows a review shortcut chip when concepts are due', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 100, level: 2, streak_count: 1, streak_freezes: 0, last_activity_date: '2026-05-02' },
      '/recommendations': {
        ...EMPTY_RECS,
        review_summary: { due_count: 2, next_due_at: '2026-05-02T10:00:00Z' },
      },
    });
    renderHome();
    expect(await screen.findByRole('link', { name: /2 to review/i })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: /shortcuts/i })).toBeInTheDocument();
  });

  it('shows portfolio and badge shortcut chips from loaded data', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 0, level: 1, streak_count: 0, streak_freezes: 0, last_activity_date: null },
      '/recommendations': EMPTY_RECS,
      '/portfolio': { cash: '25.00', total_value: '125.00', currency_code: 'USD', holdings: [] },
      '/badges': [
        { id: 'b1', name: 'First Step', description: '', condition_type: 'lesson_count', condition_value: 1 },
        { id: 'b2', name: 'Streak Star', description: '', condition_type: 'streak', condition_value: 3 },
      ],
      '/users/me/badges': [
        { id: 'b1', name: 'First Step', description: '', earned_at: '2026-05-01T10:00:00Z' },
      ],
    });
    renderHome();
    expect(await screen.findByRole('link', { name: /portfolio \$125\.00/i })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('link', { name: /badges 1 of 2/i })).toBeInTheDocument(),
    );
  });
});
