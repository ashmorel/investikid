import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ParentAuthCallback from '@/pages/ParentAuthCallback';

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/parent/auth/callback" element={<ParentAuthCallback />} />
        <Route path="/parent" element={<div>Parent Dashboard</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => { vi.spyOn(globalThis, 'fetch'); });

describe('ParentAuthCallback', () => {
  it('navigates to /parent on 200', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ status: 'signed_in', email: 'p@x.com' }), { status: 200 }),
    );
    renderAt('/parent/auth/callback?token=abc');
    await waitFor(() => expect(screen.getByText(/Parent Dashboard/)).toBeInTheDocument());
  });

  it('shows error UI on 410', async () => {
    (globalThis.fetch as any).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Link invalid' }), { status: 410 }),
    );
    renderAt('/parent/auth/callback?token=abc');
    expect(await screen.findByText(/Sign-in link expired/i)).toBeInTheDocument();
  });

  it('shows error UI when token missing', async () => {
    renderAt('/parent/auth/callback');
    expect(await screen.findByText(/Sign-in link expired/i)).toBeInTheDocument();
  });
});
