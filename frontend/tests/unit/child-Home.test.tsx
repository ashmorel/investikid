import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Home from '@/pages/child/Home';

function meBody(username = 'kid42') {
  return {
    id: 'u1', email: 'k@x.com', username, dob: '2012-01-01',
    country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
    parent_email: null, created_at: '2026-04-29T00:00:00Z',
  };
}

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
  it('greets, shows StatsBar values, and Continue card pointing at first incomplete lesson', async () => {
    mockJsonRoute({
      '/users/me': meBody('kid42'),
      '/users/me/progress': { xp: 320, level: 4, streak_count: 5, last_activity_date: '2026-05-02' },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'L1 title', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'quiz', title: 'L2 title', xp_reward: 25, order_index: 1, completed: false },
      ],
      '/recommendations': {
        next_quest: { module_id: 'mod-1', lesson_id: 'L2', reason: 'Continue where you left off' },
        suggested_modules: [],
      },
    });
    renderHome();
    expect(await screen.findByText(/Hey kid42/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/Level 4/i)).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/320 XP/i).length).toBeGreaterThanOrEqual(1);
    await waitFor(() =>
      expect(screen.getByText(/L2 title/i)).toBeInTheDocument(),
    );
    expect(screen.getByRole('link', { name: /Resume/i })).toHaveAttribute(
      'href', '/lessons/mod-1/L2',
    );
  });

  it('shows "Start" copy when user has zero completions', async () => {
    mockJsonRoute({
      '/users/me': meBody(),
      '/users/me/progress': { xp: 0, level: 1, streak_count: 0, last_activity_date: null },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'L1', xp_reward: 10, order_index: 0, completed: false },
      ],
      '/recommendations': {
        next_quest: { module_id: 'mod-1', lesson_id: 'L1', reason: 'Start your first quest' },
        suggested_modules: [],
      },
    });
    renderHome();
    expect(await screen.findByRole('link', { name: /Start/i })).toBeInTheDocument();
  });

  it('shows all-done message when every lesson is complete', async () => {
    mockJsonRoute({
      '/users/me': meBody(),
      '/users/me/progress': { xp: 100, level: 2, streak_count: 1, last_activity_date: '2026-05-02' },
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false, icon: '📈' },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'L1', xp_reward: 10, order_index: 0, completed: true },
      ],
      '/recommendations': {
        next_quest: null,
        suggested_modules: [],
      },
    });
    renderHome();
    expect(await screen.findByText(/completed all available quests/i)).toBeInTheDocument();
  });
});
