import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

import Login from '@/pages/child/Login';
import Signup from '@/pages/child/Signup';
import PendingConsent from '@/pages/child/PendingConsent';
import ConsentVerify from '@/pages/ConsentVerify';
import VerifyEmail from '@/pages/VerifyEmail';
import ForgotPassword from '@/pages/ForgotPassword';
import ResetPassword from '@/pages/ResetPassword';
import Privacy from '@/pages/Privacy';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';

function wrap(ui: React.ReactNode, initial = '/') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="*" element={<>{ui}</>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({}), { status: 200 }) as never,
  );
});

describe('a11y: auth & entry surfaces', () => {
  it('Login has no axe violations', async () => {
    const { container } = wrap(<Login />, '/login');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Signup step 1 has no axe violations', async () => {
    const { container } = wrap(<Signup />, '/signup');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('PendingConsent has no axe violations', async () => {
    const { container } = wrap(<PendingConsent />, '/pending-consent?email=k%40x.com');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ConsentVerify has no axe violations', async () => {
    const { container } = wrap(<ConsentVerify />, '/consent/verify?token=abc');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('VerifyEmail has no axe violations', async () => {
    const { container } = wrap(<VerifyEmail />, '/verify-email?token=abc');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ForgotPassword has no axe violations', async () => {
    const { container } = wrap(<ForgotPassword />, '/forgot-password');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ResetPassword has no axe violations', async () => {
    const { container } = wrap(<ResetPassword />, '/reset-password?token=abc');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Privacy has no axe violations', async () => {
    const { container } = wrap(<Privacy />, '/privacy');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ParentLogin has no axe violations', async () => {
    const { container } = wrap(<ParentLogin />, '/parent/login');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ParentAuthCallback has no axe violations', async () => {
    const { container } = wrap(<ParentAuthCallback />, '/parent/auth/callback?token=abc');
    expect(await axe(container)).toHaveNoViolations();
  });
});
