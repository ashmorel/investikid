import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PendingConsent from '@/pages/child/PendingConsent';

function renderAt(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/pending-consent" element={<PendingConsent />} />
          <Route path="/home" element={<div>Home Page</div>} />
          <Route path="/signup" element={<div>Signup Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('PendingConsent', () => {
  it('shows expired message when email param missing', () => {
    renderAt('/pending-consent');
    expect(screen.getByText(/page expired/i)).toBeInTheDocument();
  });

  it('Ive-been-approved button reveals password field', async () => {
    renderAt('/pending-consent?email=k%40x.com');
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /i've been approved/i }));
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('still-pending response shows not-approved-yet message', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Account pending parental consent' }), { status: 403 }),
    );
    renderAt('/pending-consent?email=k%40x.com');
    await userEvent.click(screen.getByRole('button', { name: /i've been approved/i }));
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/not approved yet/i)).toBeInTheDocument();
  });

  it('declined response shows declined banner', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Account access denied' }), { status: 403 }),
    );
    renderAt('/pending-consent?email=k%40x.com');
    await userEvent.click(screen.getByRole('button', { name: /i've been approved/i }));
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByText(/your parent has declined/i)).toBeInTheDocument();
  });

  it('successful recheck redirects to /home', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ token_type: 'bearer' }), { status: 200 }),
    );
    renderAt('/pending-consent?email=k%40x.com');
    await userEvent.click(screen.getByRole('button', { name: /i've been approved/i }));
    await userEvent.type(screen.getByLabelText(/password/i), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(screen.getByText('Home Page')).toBeInTheDocument());
  });
});
