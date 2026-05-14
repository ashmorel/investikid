import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from '@/components/child/Shell';

const ME = {
  id: 'u1', email: 'k@x.com', username: 'kid', dob: '2012-01-01',
  country_code: 'US', currency_code: 'USD', topic_path: 'core', is_premium: false,
  parent_email: null, created_at: '2026-04-29T00:00:00Z',
};

function renderAt(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/home" element={<div>Home Inside Shell</div>} />
          </Route>
          <Route path="/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('Shell', () => {
  it('renders username + child route on 200', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify(ME), { status: 200 }),
    );
    renderAt('/home');
    expect(await screen.findByText('Home Inside Shell')).toBeInTheDocument();
    expect(screen.getAllByText(/kid/i).length).toBeGreaterThan(0);
  });

  it('redirects to /login on 401', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid token' }), { status: 401 }),
    );
    renderAt('/home');
    await waitFor(() => expect(screen.getByText('Login Page')).toBeInTheDocument());
  });

  it('Stats link is active in nav', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify(ME), { status: 200 }),
    );
    renderAt('/home');
    await screen.findByText('Home Inside Shell');
    const statsLinks = screen.getAllByRole('link', { name: 'Stats' });
    expect(statsLinks.some(el => el.getAttribute('href') === '/stats')).toBe(true);
  });

  it('logout from profile menu navigates to /login', async () => {
    (globalThis.fetch as any)
      .mockResolvedValueOnce(new Response(JSON.stringify(ME), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ message: 'logged out' }), { status: 200 }));
    renderAt('/home');
    await screen.findByText('Home Inside Shell');
    await userEvent.click(screen.getByRole('button', { name: /account menu/i }));
    await userEvent.click(screen.getByRole('menuitem', { name: /log out/i }));
    await waitFor(() => expect(screen.getByText('Login Page')).toBeInTheDocument());
  });
});
