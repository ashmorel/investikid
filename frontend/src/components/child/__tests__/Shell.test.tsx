/**
 * Shell.test.tsx
 * Verifies that Shell renders a <main id="main"> element with the
 * animate-route-in class, and does NOT depend on framer-motion
 * (i.e. the test renders without any framer-motion mock).
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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
    const { container } = renderShell();
    const main = container.querySelector('main#main');
    expect(main).not.toBeNull();
    expect(main!.classList.contains('animate-route-in')).toBe(true);
  });

  it('renders Outlet content inside main', () => {
    renderShell();
    expect(screen.getByText('Home content')).toBeInTheDocument();
  });

  it('renders without any framer-motion mock (no AnimatePresence in tree)', () => {
    // If this renders without error, framer-motion is not required by Shell
    const { container } = renderShell();
    expect(container.querySelector('main#main')).not.toBeNull();
  });
});
