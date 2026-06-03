import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Lesson from '@/pages/child/Lesson';

vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

beforeEach(() => vi.restoreAllMocks());

// Levels fixture: one level still in_progress so destination = /lessons/mod-1/lv-1
const levelsInProgress = [
  { id: 'lv-1', module_id: 'mod-1', title: 'L1', order_index: 0, is_premium: false, icon: '', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 2, lessons_completed: 1 },
];

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
          <Route path="/lessons/:moduleId/:levelId/:lessonId" element={<Lesson />} />
          <Route path="/lessons/:moduleId/:levelId" element={<div>level screen</div>} />
          <Route path="/lessons/:moduleId" element={<div>module screen</div>} />
          <Route path="/lessons" element={<div>modules screen</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Lesson shell', () => {
  it('loads card lesson, completes, and shows CompletionPanel with Continue button', async () => {
    mockJsonRoute({
      'GET /lessons/L1': {
        id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
        completed: false, locked: false,
        content_json: { title: 'CardT', body: 'CardB' },
      },
      'GET /levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
        { id: 'L2', type: 'card', title: 'NextT', xp_reward: 10, order_index: 1, completed: false },
      ],
      'GET /modules/mod-1/levels': levelsInProgress,
      'POST /lessons/L1/complete': {
        xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1,
        practice_available: false,
      },
    });
    renderAt('/lessons/mod-1/lv-1/L1');
    expect(await screen.findByRole('heading', { name: /CardT/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Got it/ }));
    await waitFor(() => expect(screen.getByText(/\+10/)).toBeInTheDocument());
    // Continue button present
    expect(screen.getByRole('button', { name: /Continue/ })).toBeInTheDocument();
  });

  it('clicking Continue navigates to level list when more quests remain in level', async () => {
    mockJsonRoute({
      'GET /lessons/L1': {
        id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
        completed: false, locked: false,
        content_json: { title: 'CardT', body: 'CardB' },
      },
      'GET /levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
        { id: 'L2', type: 'card', title: 'NextT', xp_reward: 10, order_index: 1, completed: false },
      ],
      'GET /modules/mod-1/levels': levelsInProgress,
      'POST /lessons/L1/complete': {
        xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1,
        practice_available: false,
      },
    });
    renderAt('/lessons/mod-1/lv-1/L1');
    await screen.findByRole('heading', { name: /CardT/i });
    fireEvent.click(screen.getByRole('button', { name: /Got it/ }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Continue/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    // Should navigate to the level's quest list
    await waitFor(() => expect(screen.getByText('level screen')).toBeInTheDocument());
  });

  it('clicking Continue navigates to module list when all levels are complete', async () => {
    const allDone = [
      { id: 'lv-1', module_id: 'mod-1', title: 'L1', order_index: 0, is_premium: false, icon: '', state: 'completed', locked_reason: null, passed: true, lessons_total: 1, lessons_completed: 1 },
    ];
    mockJsonRoute({
      'GET /lessons/L1': {
        id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
        completed: false, locked: false,
        content_json: { title: 'CardT', body: 'CardB' },
      },
      'GET /levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
      ],
      'GET /modules/mod-1/levels': allDone,
      'POST /lessons/L1/complete': {
        xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1,
        practice_available: false,
      },
    });
    renderAt('/lessons/mod-1/lv-1/L1');
    await screen.findByRole('heading', { name: /CardT/i });
    fireEvent.click(screen.getByRole('button', { name: /Got it/ }));
    await waitFor(() => expect(screen.getByRole('button', { name: /Continue/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    await waitFor(() => expect(screen.getByText('modules screen')).toBeInTheDocument());
  });

  it('does not submit completion twice while progress is saving', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : input.toString();
      const method = (init?.method ?? 'GET').toUpperCase();
      const key = `${method} ${url}`;
      if (key === 'GET /lessons/L1') {
        return new Response(JSON.stringify({
          id: 'L1', module_id: 'mod-1', type: 'card', xp_reward: 10, order_index: 0,
          completed: false, locked: false,
          content_json: { title: 'CardT', body: 'CardB' },
        }), { status: 200 });
      }
      if (key === 'GET /levels/lv-1/lessons') {
        return new Response(JSON.stringify([
          { id: 'L1', type: 'card', title: 'CardT', xp_reward: 10, order_index: 0, completed: false },
        ]), { status: 200 });
      }
      if (key === 'GET /modules/mod-1/levels') {
        return new Response(JSON.stringify(levelsInProgress), { status: 200 });
      }
      if (key === 'POST /lessons/L1/complete') {
        return new Promise<Response>((resolve) => {
          setTimeout(() => resolve(new Response(JSON.stringify({
            xp_awarded: 10, already_completed: false, total_xp: 10, level: 1, streak_count: 1,
            practice_available: false,
          }), { status: 200 })), 100);
        });
      }
      return new Response('not mocked: ' + key, { status: 500 });
    });

    renderAt('/lessons/mod-1/lv-1/L1');
    const button = await screen.findByRole('button', { name: /Got it/ });
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => {
      const completionPosts = fetchSpy.mock.calls.filter(([input, init]) => {
        const url = typeof input === 'string' ? input : input.toString();
        return url === '/lessons/L1/complete' && (init?.method ?? 'GET').toUpperCase() === 'POST';
      });
      expect(completionPosts).toHaveLength(1);
    });

    await waitFor(() => expect(screen.getByText(/\+10/)).toBeInTheDocument());
  });
});
