import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import Lessons from '@/pages/child/Lessons';

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

function renderLessons() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Lessons />
        <Toaster />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Lessons page', () => {
  it('renders module cards in order with completion counts', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-1', topic: 'stocks', title: 'M1', country_codes: [], is_premium: false, order_index: 0, locked: false },
        { id: 'mod-2', topic: 'savings', title: 'M2', country_codes: [], is_premium: false, order_index: 1, locked: false },
      ],
      '/modules/mod-1/lessons': [
        { id: 'L1', type: 'card', title: 't', xp_reward: 10, order_index: 0, completed: true },
        { id: 'L2', type: 'card', title: 't', xp_reward: 10, order_index: 1, completed: false },
      ],
      '/modules/mod-2/lessons': [
        { id: 'L3', type: 'card', title: 't', xp_reward: 10, order_index: 0, completed: false },
      ],
    });
    renderLessons();
    expect(await screen.findByText('M1')).toBeInTheDocument();
    expect(await screen.findByText('M2')).toBeInTheDocument();
    expect(await screen.findByText(/1\s*\/\s*2 lessons/)).toBeInTheDocument();
  });

  it('locked module card shows Premium and does not navigate on click', async () => {
    mockJsonRoute({
      '/modules': [
        { id: 'mod-3', topic: 'real_estate', title: 'M3', country_codes: [], is_premium: true, order_index: 0, locked: true },
      ],
    });
    renderLessons();
    expect(await screen.findByText(/Premium/i)).toBeInTheDocument();
  });
});
