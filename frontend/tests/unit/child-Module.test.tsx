import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
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
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/lessons/:moduleId" element={<Module />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Module page', () => {
  it('renders module title, completion count, and lessons in order with status icons', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'Stocks 101', country_codes: [], is_premium: false, order_index: 0, locked: false },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 'First', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'quiz', title: 'Second', xp_reward: 25, order_index: 1, completed: false },
        { id: 'L3', type: 'card', title: 'Third', xp_reward: 10, order_index: 2, completed: false },
      ],
    });
    renderAt('/lessons/mod-1');
    expect(await screen.findByRole('heading', { name: /Stocks 101/i })).toBeInTheDocument();
    expect(await screen.findByText(/1\s*\/\s*3 quests complete/i)).toBeInTheDocument();
    expect(await screen.findByText(/1\. First/)).toBeInTheDocument();
    expect(screen.getByLabelText('completed')).toBeInTheDocument();
    expect(screen.getByLabelText('next up')).toBeInTheDocument();
    expect(screen.getByLabelText('not started')).toBeInTheDocument();
  });
});
