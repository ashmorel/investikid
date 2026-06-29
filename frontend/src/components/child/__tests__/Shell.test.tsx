/**
 * Shell.test.tsx
 * Verifies that Shell renders a <main id="main"> element with the
 * animate-route-in class, and does NOT depend on framer-motion
 * (i.e. the test renders without any framer-motion mock).
 *
 * Also covers the diagnostic gate (Task 3):
 *   - has_baseline === false (loaded) → Navigate to /onboarding/diagnostic
 *   - has_baseline === true → renders app content normally
 *   - evidence loading → renders app content (fail-open)
 *   - evidence error → renders app content (fail-open)
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ── Controllable evidence mock ───────────────────────────────────────────────
const mockUseEvidence = vi.fn();
vi.mock('@/api/diagnostic', () => ({
  useEvidence: () => mockUseEvidence(),
}));

// ── Mock every hook / API used by Shell ──────────────────────────────────────
vi.mock('@/hooks/useChildSession', () => ({
  useChildSession: () => ({
    data: {
      id: '1',
      username: 'Sam',
      email: 's@b.com',
      dob: '',
      country_code: 'GB',
      currency_code: 'GBP',
      topic_path: null,
      is_premium: false,
      is_admin: false,
      parent_email: null,
      created_at: '',
      email_verified_at: null,
    },
    isLoading: false,
    error: null,
  }),
}));

vi.mock('@/hooks/useChildAuthGuard', () => ({ useChildAuthGuard: () => undefined }));
vi.mock('@/hooks/useSwipeNav', () => ({ useSwipeNav: () => undefined }));
vi.mock('@/hooks/usePullToRefresh', () => ({
  usePullToRefresh: () => ({ indicatorProps: { isRefreshing: false, pullProgress: 0 } }),
}));
vi.mock('@/hooks/useStreakReminder', () => ({ useStreakReminder: () => undefined }));
vi.mock('@/components/a11y/useRouteFocus', () => ({ useRouteFocus: () => undefined }));
vi.mock('@/api/ai', () => ({ useRecommendations: () => ({ data: null }) }));
vi.mock('@/hooks/usePremiumPaywall', () => ({
  PremiumPaywallProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  usePremiumPaywall: () => ({ open: vi.fn() }),
}));

// Stub heavy child components
vi.mock('@/components/child/TopNav', () => ({ TopNav: () => <div data-testid="top-nav" /> }));
vi.mock('@/components/child/TierBadge', () => ({ TierBadge: () => null }));
vi.mock('@/components/child/BottomTabBar', () => ({ BottomTabBar: () => null }));
vi.mock('@/components/VerifyEmailBanner', () => ({ VerifyEmailBanner: () => null }));
vi.mock('@/components/mobile/PullToRefreshIndicator', () => ({ PullToRefreshIndicator: () => null }));
vi.mock('@/components/a11y/SkipLink', () => ({ SkipLink: () => null }));
vi.mock('@/components/a11y/RouteErrorBoundary', () => ({
  RouteErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock('@/components/child/PennyFAB', () => ({ PennyFAB: () => null }));
vi.mock('@/components/child/CoachPanel', () => ({ CoachPanel: () => null }));
vi.mock('@/api/cosmetics', () => ({
  useEquippedCosmetics: () => ({ accessories: [], skin: null, background: null }),
}));

// ── Import Shell AFTER mocks ──────────────────────────────────────────────────
import { Shell } from '../Shell';

function renderShell(path = '/home') {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          {/* Diagnostic route outside Shell — mirrors App.tsx */}
          <Route path="/onboarding/diagnostic" element={<p>Diagnostic page</p>} />
          <Route element={<Shell />}>
            <Route path="/home" element={<p>Home content</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Shell', () => {
  it('renders <main id="main"> with animate-route-in class', () => {
    mockUseEvidence.mockReturnValue({ data: { has_baseline: true }, isLoading: false, isError: false });
    const { container } = renderShell();
    const main = container.querySelector('main#main');
    expect(main).not.toBeNull();
    expect(main!.classList.contains('animate-route-in')).toBe(true);
  });

  it('renders Outlet content inside main', () => {
    mockUseEvidence.mockReturnValue({ data: { has_baseline: true }, isLoading: false, isError: false });
    renderShell();
    expect(screen.getByText('Home content')).toBeInTheDocument();
  });

  it('renders without any framer-motion mock (no AnimatePresence in tree)', () => {
    mockUseEvidence.mockReturnValue({ data: { has_baseline: true }, isLoading: false, isError: false });
    // If this renders without error, framer-motion is not required by Shell
    const { container } = renderShell();
    expect(container.querySelector('main#main')).not.toBeNull();
  });
});

// ── Diagnostic gate (Task 3) ─────────────────────────────────────────────────
describe('Shell diagnostic gate', () => {
  it('redirects to /onboarding/diagnostic when has_baseline is false (loaded)', () => {
    mockUseEvidence.mockReturnValue({
      data: { has_baseline: false },
      isLoading: false,
      isError: false,
    });
    renderShell('/home');
    expect(screen.getByText('Diagnostic page')).toBeInTheDocument();
    expect(screen.queryByText('Home content')).not.toBeInTheDocument();
  });

  it('renders app normally when has_baseline is true', () => {
    mockUseEvidence.mockReturnValue({
      data: { has_baseline: true },
      isLoading: false,
      isError: false,
    });
    renderShell('/home');
    expect(screen.getByText('Home content')).toBeInTheDocument();
    expect(screen.queryByText('Diagnostic page')).not.toBeInTheDocument();
  });

  it('renders app normally when evidence is loading (fail-open)', () => {
    mockUseEvidence.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    renderShell('/home');
    expect(screen.getByText('Home content')).toBeInTheDocument();
    expect(screen.queryByText('Diagnostic page')).not.toBeInTheDocument();
  });

  it('renders app normally when evidence query errors (fail-open)', () => {
    mockUseEvidence.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });
    renderShell('/home');
    expect(screen.getByText('Home content')).toBeInTheDocument();
    expect(screen.queryByText('Diagnostic page')).not.toBeInTheDocument();
  });
});
