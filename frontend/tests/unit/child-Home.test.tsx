import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
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
      <MemoryRouter>
        <Home />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('Home', () => {
  it('shows StatsBar values and renders module tiles', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 320, level: 4, streak_count: 5, last_activity_date: '2026-05-02' },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
        { id: 'mod-2', topic: 'savings', title: 'Savings Basics', country_codes: [], is_premium: false, order_index: 1, locked: false, icon: '💰' },
      ],
      '/recommendations': {
        continue_learning: [
          { module_id: 'mod-1', lesson_id: 'L2', score: 0.8, reason: 'Keep going!', review_prompt: null, weak_concepts: [] },
        ],
        practise_again: [],
        something_new: [],
        review_summary: { due_count: 0, next_due_at: null },
      },
    });
    renderHome();
    expect((await screen.findAllByText(/Level 4/i)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/320 XP/i).length).toBeGreaterThanOrEqual(1);
    await waitFor(() =>
      expect(screen.getByText(/Stocks 101/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Savings Basics/i)).toBeInTheDocument();
  });

  it('renders the module grid when modules are returned', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 0, level: 1, streak_count: 0, last_activity_date: null },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
      ],
      '/recommendations': {
        continue_learning: [],
        practise_again: [],
        something_new: [],
        review_summary: { due_count: 0, next_due_at: null },
      },
    });
    renderHome();
    await waitFor(() =>
      expect(screen.getByText(/Stocks/i)).toBeInTheDocument(),
    );
    expect(screen.getByText(/Your quests/i)).toBeInTheDocument();
  });

  it('shows review banner when concepts are due', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 100, level: 2, streak_count: 1, last_activity_date: '2026-05-02' },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
      ],
      '/recommendations': {
        continue_learning: [],
        practise_again: [
          { module_id: 'mod-1', lesson_id: null, score: 0.6, reason: 'Review time!', review_prompt: '2 concepts to review', weak_concepts: ['APR', 'compound interest'] },
        ],
        something_new: [],
        review_summary: { due_count: 2, next_due_at: '2026-05-02T10:00:00Z' },
      },
    });
    renderHome();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/2 concepts/i)).toBeInTheDocument();
  });

  it('marks the recommended module tile', async () => {
    mockJsonRoute({
      '/users/me/progress': { xp: 50, level: 1, streak_count: 0, last_activity_date: null },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
        { id: 'mod-2', topic: 'savings', title: 'Savings', country_codes: [], is_premium: false, order_index: 1, locked: false, icon: '💰' },
      ],
      '/recommendations': {
        continue_learning: [
          { module_id: 'mod-1', lesson_id: 'L1', score: 0.9, reason: 'Continue', review_prompt: null, weak_concepts: [] },
        ],
        practise_again: [],
        something_new: [],
        review_summary: { due_count: 0, next_due_at: null },
      },
    });
    renderHome();
    await waitFor(() => expect(screen.getByText(/Stocks/i)).toBeInTheDocument());
    // The recommended tile shows the "Next" badge
    expect(screen.getByText(/Next/i)).toBeInTheDocument();
  });
});
