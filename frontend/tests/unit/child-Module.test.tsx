import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import Module from '@/pages/child/Module';

beforeEach(() => vi.restoreAllMocks());

function mockJsonRoute(routeMap: Record<string, unknown>) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : input.toString();
    for (const [path, body] of Object.entries(routeMap)) {
      if (url === path) return new Response(JSON.stringify(body), { status: 200 });
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
            <Route path="/lessons/:moduleId" element={<Module />} />
          </Routes>
          <Toaster />
        </MemoryRouter>
      </PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

describe('Module page', () => {
  it('renders module title, level count, and a LevelCard per level', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Beginner', order_index: 0, is_premium: false, icon: '🌱', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 3, lessons_completed: 1 },
        { id: 'lv-2', module_id: 'mod-1', title: 'Intermediate', order_index: 1, is_premium: false, icon: '📊', state: 'locked', locked_reason: 'progression', passed: false, lessons_total: 3, lessons_completed: 0 },
      ],
    });
    renderAt('/lessons/mod-1');
    expect(await screen.findByRole('heading', { name: /Stocks 101/i })).toBeInTheDocument();
    expect(await screen.findByText(/^2 levels$/i)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /Beginner/i })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /Intermediate/i })).toBeInTheDocument();
  });

  it('frames a single-level module as lessons (not "1 level")', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'What is a stock', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Level 1', order_index: 0, is_premium: false, icon: '🌱', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 4, lessons_completed: 1 },
      ],
    });
    renderAt('/lessons/mod-1');
    expect(await screen.findByText(/^4 lessons$/i)).toBeInTheDocument();
    expect(screen.queryByText(/^1 level$/i)).not.toBeInTheDocument();
    expect(screen.getByText(/1 \/ 4 lessons complete/i)).toBeInTheDocument();
  });

  it('shows a "Module complete" next-module CTA when every level is done', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'What is a stock', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
        { id: 'mod-2', topic: 'savings', title: 'Saving Basics', country_codes: [], is_premium: false, order_index: 1, icon: '🏦', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Level 1', order_index: 0, is_premium: false, icon: '🌱', state: 'completed', locked_reason: null, passed: true, lessons_total: 4, lessons_completed: 4 },
      ],
    });
    renderAt('/lessons/mod-1');
    expect(await screen.findByText(/Module complete/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Next: Saving Basics/i })).toBeInTheDocument();
  });

  it('shows "Back to all modules" when the finished module is the last one', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'What is a stock', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Level 1', order_index: 0, is_premium: false, icon: '🌱', state: 'completed', locked_reason: null, passed: true, lessons_total: 4, lessons_completed: 4 },
      ],
    });
    renderAt('/lessons/mod-1');
    expect(await screen.findByRole('button', { name: /Back to all modules/i })).toBeInTheDocument();
  });

  it('toasts "Finish the previous level first." when progression-locked level clicked', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Locked Level', order_index: 0, is_premium: false, icon: '🔒', state: 'locked', locked_reason: 'progression', passed: false, lessons_total: 3, lessons_completed: 0 },
      ],
    });
    renderAt('/lessons/mod-1');
    const btn = await screen.findByRole('button', { name: /Locked Level/i });
    await userEvent.click(btn);
    expect(await screen.findByText(/Finish the previous level first\./i)).toBeInTheDocument();
  });

  it('tapping a premium-locked level opens the paywall', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, icon: '📈', locked: false },
      ],
      '/modules/mod-1/levels': [
        { id: 'lv-1', module_id: 'mod-1', title: 'Advanced', order_index: 1, is_premium: true, icon: '⭐', state: 'locked', locked_reason: 'premium', passed: false, lessons_total: 3, lessons_completed: 0 },
      ],
    });
    renderAt('/lessons/mod-1');
    const btn = await screen.findByRole('button', { name: /Advanced/i });
    await userEvent.click(btn);
    // The paywall sheet replaces the old toast.
    expect(await screen.findByText(/premium unlocks/i)).toBeInTheDocument();
    expect(screen.queryByText(/Ask a grown-up to unlock\./i)).not.toBeInTheDocument();
  });
});
