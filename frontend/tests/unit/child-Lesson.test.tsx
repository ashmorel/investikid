import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Lesson from '@/pages/child/Lesson';

vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

beforeEach(() => vi.restoreAllMocks());

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method ?? 'GET').toUpperCase();
    const key = `${method} ${url}`;
    for (const [path, body] of Object.entries(routeMap)) {
      if (key === path) return new Response(JSON.stringify(body), { status: 200 });
    }
    return new Response('not mocked: ' + key, { status: 500 });
  });
}

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/lessons/:moduleId/:lessonId" element={<Lesson />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Lesson shell', () => {
  it('loads card lesson, completes, and shows CompletionPanel with Next link', async () => {
    mockJsonRoute({
      'GET /lessons/L1': {
        id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
        completed: false, locked: false,
        content_json: { title: 'CardT', body: 'CardB' },
      },
      'GET /modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
        { id: 'L2', type: 'card', title: 'NextT', xp_reward: 10, order_index: 1, completed: false },
      ],
      'POST /lessons/L1/complete': {
        xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1,
      },
    });
    renderAt('/lessons/mod-1/L1');
    expect(await screen.findByRole('heading', { name: /CardT/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Got it/ }));
    await waitFor(() => expect(screen.getByText(/\+10 XP/)).toBeInTheDocument());
    expect(screen.getByRole('link', { name: /Next Quest/ })).toHaveAttribute(
      'href', '/lessons/mod-1/L2',
    );
  });
});
