import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import Level from '@/pages/child/Level';

beforeEach(() => vi.restoreAllMocks());

function mockJsonRoute(routeMap: Record<string, unknown>, statusMap: Record<string, number> = {}) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url === path) {
        const status = statusMap[path] ?? 200;
        return new Response(typeof body === 'string' ? body : JSON.stringify(body), { status });
      }
    }
    return new Response('not mocked: ' + url, { status: 500 });
  });
}

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/lessons/:moduleId/:levelId" element={<Level />} />
          </Routes>
        </MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

describe('Level page', () => {
  it('renders lesson rows with completion counts and links', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'quiz', title: 'Second', xp_reward: 25, order_index: 1, completed: false },
        { id: 'L3', type: 'card', title: 'Third', xp_reward: 10, order_index: 2, completed: false },
      ],
    });
    renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/1 \/ 3 lessons/i)).toBeInTheDocument();
    expect(await screen.findByText(/1\. First/)).toBeInTheDocument();
    expect(screen.getByLabelText('completed')).toBeInTheDocument();
    expect(screen.getByLabelText('next up')).toBeInTheDocument();
    expect(screen.getByLabelText('not started')).toBeInTheDocument();
    // Lesson links use 3-segment path
    const links = screen.getAllByRole('link');
    const lessonLinks = links.filter((l) => l.getAttribute('href')?.startsWith('/lessons/mod-1/lv-1/'));
    expect(lessonLinks.length).toBeGreaterThan(0);
  });

  it('shows back link to module levels page', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [],
    });
    renderAt('/lessons/mod-1/lv-1');
    const back = await screen.findByRole('link', { name: /back to levels/i });
    expect(back).toHaveAttribute('href', '/lessons/mod-1');
  });

  it('shows the objectives intro block when the level has learning_objectives', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 1, lessons_completed: 0, learning_objectives: ['What a stock is', 'Why companies sell shares'], mastered_at: null },
      ],
    });
    renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/in this level you'll learn/i)).toBeInTheDocument();
    const list = screen.getByRole('list', { name: /you'll learn/i });
    expect(list).toBeInTheDocument();
    expect(screen.getByText('What a stock is')).toBeInTheDocument();
    expect(screen.getByText('Why companies sell shares')).toBeInTheDocument();
  });

  it('hides the objectives block when the level has no learning_objectives', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 1, lessons_completed: 0, learning_objectives: null, mastered_at: null },
      ],
    });
    renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/1\. First/)).toBeInTheDocument();
    expect(screen.queryByText(/in this level you'll learn/i)).not.toBeInTheDocument();
  });

  it('shows a Mastered stamp with the date when mastered_at is set', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: true },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'completed', locked_reason: null, passed: true, lessons_total: 1, lessons_completed: 1, learning_objectives: null, mastered_at: '2026-06-11T09:30:00Z' },
      ],
    });
    renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/Mastered/)).toBeInTheDocument();
    expect(screen.getByText(/11 Jun 2026/)).toBeInTheDocument();
  });

  it('shows no Mastered stamp when mastered_at is null', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 1, lessons_completed: 0, learning_objectives: null, mastered_at: null },
      ],
    });
    renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/1\. First/)).toBeInTheDocument();
    expect(screen.queryByText(/Mastered/)).not.toBeInTheDocument();
  });

  it('has no axe violations with objectives and mastered stamp', async () => {
    mockJsonRoute({
      '/levels/lv-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: true },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'completed', locked_reason: null, passed: true, lessons_total: 1, lessons_completed: 1, learning_objectives: ['What a stock is'], mastered_at: '2026-06-11T09:30:00Z' },
      ],
    });
    const { container } = renderAt('/lessons/mod-1/lv-1');
    expect(await screen.findByText(/Mastered/)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('opens the paywall on a premium_required 403 error', async () => {
    mockJsonRoute(
      {
        '/levels/lv-1/lessons': JSON.stringify({
          detail: { message: 'Premium required', code: 'premium_required', context: { label: 'Advanced' } },
        }),
      },
      { '/levels/lv-1/lessons': 403 },
    );
    renderAt('/lessons/mod-1/lv-1');
    // The paywall sheet auto-opens; the placeholder (behind the modal, hidden
    // from the a11y tree) offers to re-open it.
    expect(await screen.findByText(/premium unlocks/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /See what's included/i, hidden: true })).toBeInTheDocument();
    expect(screen.queryByText(/This level is premium\./i)).not.toBeInTheDocument();
  });
});
