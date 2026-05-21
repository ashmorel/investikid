import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from '@/components/child/Shell';

const ME = {
  id: 'u1',
  email: 'k@x.com',
  username: 'kid',
  dob: '2012-01-01',
  country_code: 'US',
  currency_code: 'USD',
  topic_path: 'core',
  is_premium: false,
  parent_email: null,
  created_at: '2026-04-29T00:00:00Z',
};

beforeEach(() => {
  // Force prefers-reduced-motion: reduce
  window.matchMedia = vi.fn().mockImplementation((q: string) => ({
    matches: q.includes('reduce'),
    media: q,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(ME), { status: 200 }) as never,
  );
});

describe('reduced-motion', () => {
  it('Shell honours prefers-reduced-motion (no translate transform on main)', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
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
    await waitFor(() =>
      expect(container.textContent).toContain('HomeRouteContent'),
    );
    const main = container.querySelector('main#main') as HTMLElement;
    expect(main).toBeTruthy();
    // When reduced-motion is set, framer-motion does not apply a transform animation.
    expect(main.style.transform || '').not.toMatch(/translateY|matrix/);
  });
});
