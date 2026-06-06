import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ParentDashboard from '@/pages/ParentDashboard';

// Prevent SubscriptionCard from racing with the children fetch mock
vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: () => new Promise(() => {}), // never resolves → card stays hidden
    createCheckout: () => new Promise(() => {}),
    createPortal: () => new Promise(() => {}),
  },
}));

// Prevent SignInMethods from interfering with fetch mock
vi.mock('@/api/parentAuth', () => ({
  parentAuthApi: {
    listIdentities: () => new Promise(() => {}), // never resolves → section stays in loading state
    linkProvider: vi.fn(),
    unlinkProvider: vi.fn(),
  },
}));
vi.mock('@/lib/socialLogin', () => ({ socialIdToken: vi.fn() }));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/parent']}>
        <Routes>
          <Route path="/parent" element={<ParentDashboard />} />
          <Route path="/parent/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('ParentDashboard', () => {
  it('shows empty state when no children', async () => {
    (globalThis.fetch as any).mockImplementation(
      async () => new Response(JSON.stringify([]), { status: 200 }),
    );
    renderPage();
    expect(await screen.findByText(/No children linked/i)).toBeInTheDocument();
  });

  it('renders one card per child', async () => {
    const children = [
      { user_id: 'u1', username: 'kid1', country_code: 'GB', is_active: true,
        parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
        deleted_at: null, deletion_requested_at: null },
      { user_id: 'u2', username: 'kid2', country_code: 'US', is_active: true,
        parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
        deleted_at: null, deletion_requested_at: null },
    ];
    (globalThis.fetch as any).mockImplementation(async (input: RequestInfo | URL) => {
      const body = String(input).includes('/parent/groups') ? [] : children;
      return new Response(JSON.stringify(body), { status: 200 });
    });
    renderPage();
    // Names also appear in the Groups child <select>, so scope to the card heading.
    expect(await screen.findByRole('heading', { name: 'kid1' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'kid2' })).toBeInTheDocument();
  });

  it('redirects to /parent/login on 401', async () => {
    (globalThis.fetch as any).mockImplementation(
      async () => new Response(JSON.stringify({ detail: 'Not authenticated' }), { status: 401 }),
    );
    renderPage();
    await waitFor(() => expect(screen.getByText('Login Page')).toBeInTheDocument());
  });
});
