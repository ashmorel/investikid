import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import VerifyEmail from '@/pages/VerifyEmail';
import type { Me } from '@/api/auth';

const UNVERIFIED_ME: Me = {
  id: 'u1',
  email: 'kid@example.com',
  username: 'kid',
  dob: '2012-01-01',
  country_code: 'US',
  currency_code: 'USD',
  topic_path: null,
  is_premium: false,
  is_admin: false,
  parent_email: null,
  created_at: '2026-01-01T00:00:00Z',
  email_verified_at: null,
};

function renderVerifyEmail(qc: QueryClient) {
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/verify-email?token=tok_123']}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('VerifyEmail', () => {
  it('refreshes cached profile data when verification succeeds', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
    );
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    qc.setQueryData(['me'], UNVERIFIED_ME);

    renderVerifyEmail(qc);

    expect(await screen.findByRole('heading', { name: /email verified/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(qc.getQueryData<Me>(['me'])?.email_verified_at).not.toBeNull();
    });
  });
});
