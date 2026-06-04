import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Login from '@/pages/child/Login';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/home" element={<div>Home Page</div>} />
          <Route path="/pending-consent" element={<div>Pending Consent</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('Login', () => {
  it('uses the safe centered auth layout on mobile', () => {
    const { container } = renderPage();
    expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
    const main = container.querySelector('main');
    expect(main).toHaveClass('min-h-[100svh]');
    expect(main).toHaveClass('items-center');
    expect(main).toHaveClass('overflow-x-hidden');
  });

  it('redirects to /home on success', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ token_type: 'bearer' }), { status: 200 }),
    );
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'a@x.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(screen.getByText('Home Page')).toBeInTheDocument());
  });

  it('redirects to /pending-consent on 403 consent error', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Account pending parental consent' }), { status: 403 }),
    );
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'kid@x.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(screen.getByText('Pending Consent')).toBeInTheDocument());
  });

  it('shows generic error on 401', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Invalid credentials' }), { status: 401 }),
    );
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'a@x.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/Email or password incorrect/i)).toBeInTheDocument();
  });

  it('shows access-denied error on 403 generic', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Account access denied' }), { status: 403 }),
    );
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'a@x.com');
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/Account access denied/i)).toBeInTheDocument();
  });
});
