import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import ParentLogin from '@/pages/ParentLogin';

// Mock the social login wrapper so the native plugin never loads in jsdom
vi.mock('@/lib/socialLogin', () => ({
  socialIdToken: vi.fn(),
}));

// Mock the parent auth API
vi.mock('@/api/parentAuth', () => ({
  parentAuthApi: {
    oauthSignIn: vi.fn(),
    linkProvider: vi.fn(),
    unlinkProvider: vi.fn(),
    listIdentities: vi.fn(),
  },
}));

import { socialIdToken } from '@/lib/socialLogin';
import { parentAuthApi } from '@/api/parentAuth';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/parent/login']}>
        <Routes>
          <Route path="/parent/login" element={<ParentLogin />} />
          <Route path="/parent" element={<div>Parent Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch');
  vi.clearAllMocks();
});

describe('ParentLogin', () => {
  it('rejects invalid email on submit', async () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /parents' sign-in/i })).toBeInTheDocument();
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

  it('renders Continue with Apple and Continue with Google buttons', () => {
    renderPage();
    expect(screen.getByRole('button', { name: /continue with apple/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
  });

  it('clicking Continue with Google calls socialIdToken then oauthSignIn then navigates to /parent', async () => {
    const mockIdToken = 'google-id-token-abc';
    const mockNonce = 'nonce-xyz';
    (socialIdToken as ReturnType<typeof vi.fn>).mockResolvedValue({ idToken: mockIdToken, nonce: mockNonce });
    (parentAuthApi.oauthSignIn as ReturnType<typeof vi.fn>).mockResolvedValue({ status: 'signed_in', email: 'p@x.com' });

    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /continue with google/i }));

    await waitFor(() => {
      expect(socialIdToken).toHaveBeenCalledWith('google');
      expect(parentAuthApi.oauthSignIn).toHaveBeenCalledWith('google', mockIdToken, mockNonce);
    });
    expect(await screen.findByText(/Parent Dashboard/i)).toBeInTheDocument();
  });

  it('shows friendly error when oauthSignIn rejects', async () => {
    (socialIdToken as ReturnType<typeof vi.fn>).mockResolvedValue({ idToken: 'tok', nonce: 'n' });
    (parentAuthApi.oauthSignIn as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('404'));

    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /continue with google/i }));

    expect(
      await screen.findByText(/couldn't sign you in/i),
    ).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });
});
