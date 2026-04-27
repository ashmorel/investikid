import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ParentLogin from '@/pages/ParentLogin';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><ParentLogin /></MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('ParentLogin', () => {
  it('rejects invalid email on submit', async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email');
    await userEvent.click(screen.getByRole('button', { name: /send sign-in link/i }));
    expect(screen.getByText(/valid email/i)).toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it('submits and shows confirmation message', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ status: 'queued' }), { status: 202 }),
    );
    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), 'parent@example.com');
    await userEvent.click(screen.getByRole('button', { name: /send sign-in link/i }));
    expect(await screen.findByText(/Check your inbox/i)).toBeInTheDocument();
    expect(screen.getByText(/parent@example\.com/)).toBeInTheDocument();
  });
});
