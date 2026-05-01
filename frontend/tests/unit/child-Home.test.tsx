import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Home from '@/pages/child/Home';

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({
      id: 'u1', email: 'k@x.com', username: 'kid42', dob: '2012-01-01',
      country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
      parent_email: null, created_at: '2026-04-29T00:00:00Z',
    }), { status: 200 }),
  );
});

describe('Home', () => {
  it('greets with username from /users/me', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <Home />
      </QueryClientProvider>,
    );
    expect(await screen.findByText(/Welcome, kid42!/i)).toBeInTheDocument();
  });
});
