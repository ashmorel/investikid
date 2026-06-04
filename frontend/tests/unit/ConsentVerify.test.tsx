import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ConsentVerify from '@/pages/ConsentVerify';

function renderAt(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes><Route path="/consent/verify" element={<ConsentVerify />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('ConsentVerify', () => {
  it('shows error when token missing', () => {
    renderAt('/consent/verify');
    expect(screen.getByText(/Invalid link/i)).toBeInTheDocument();
  });

  it('renders child summary on success and approves', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce(
      new Response(JSON.stringify({ username: 'kid', age: 11, country_code: 'GB' }), { status: 200 }),
    ).mockResolvedValueOnce(
      new Response(JSON.stringify({ status: 'ok', decision: 'approve' }), { status: 200 }),
    );
    renderAt('/consent/verify?token=abc');
    expect(await screen.findByRole('heading', { name: /approve your child's account/i })).toBeInTheDocument();
    expect(await screen.findByText(/kid/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /approve/i }));
    await waitFor(() => expect(screen.getByRole('heading', { name: /all set/i })).toBeInTheDocument());
  });

  it('shows 410 error when verify returns 410', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Already decided' }), { status: 410 }),
    );
    renderAt('/consent/verify?token=abc');
    expect(await screen.findByRole('heading', { name: /link unavailable/i, level: 1 })).toBeInTheDocument();
  });
});
