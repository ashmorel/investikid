import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

import ParentDashboard from '@/pages/ParentDashboard';

function wrap(ui: React.ReactNode, initial = '/parent') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/parent" element={<>{ui}</>} />
          <Route path="/parent/login" element={<div>Login Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => vi.restoreAllMocks());

describe('a11y: parent surfaces', () => {
  it('ParentDashboard empty state has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200 }) as never,
    );
    const { container } = wrap(<ParentDashboard />);
    await waitFor(() => expect(screen.getByText(/No children linked/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ParentDashboard with children has no axe violations', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            user_id: 'u1', username: 'kid1', country_code: 'GB', is_active: true,
            parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
            deleted_at: null, deletion_requested_at: null,
          },
          {
            user_id: 'u2', username: 'kid2', country_code: 'US', is_active: true,
            parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
            deleted_at: null, deletion_requested_at: null,
          },
        ]),
        { status: 200 },
      ) as never,
    );
    const { container } = wrap(<ParentDashboard />);
    await waitFor(() => expect(screen.getByText('kid1')).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
