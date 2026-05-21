import { it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from '@/components/child/Shell';

const ME = {
  id: 'u1', email: 'k@x.com', username: 'kid', dob: '2012-01-01',
  country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
  parent_email: null, created_at: '2026-04-29T00:00:00Z',
};

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(ME), { status: 200 }) as never,
  );
});

it('Shell renders SkipLink and main#main[tabindex=-1]', async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/home" element={<div>HomeRouteContent</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText('HomeRouteContent')).toBeInTheDocument());
  expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute('href', '#main');
  const main = document.querySelector('main#main')!;
  expect(main).toBeTruthy();
  expect(main).toHaveAttribute('tabindex', '-1');
});
