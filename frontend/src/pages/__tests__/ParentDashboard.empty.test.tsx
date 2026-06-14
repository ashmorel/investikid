import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Stub heavy child components
vi.mock('@/components/SubscriptionCard', () => ({ SubscriptionCard: () => null }));
vi.mock('@/components/parent/SignInMethods', () => ({ SignInMethods: () => null }));
vi.mock('@/components/parent/GroupsCard', () => ({ GroupsCard: () => null }));
vi.mock('@/components/parent/NotificationPreferencesCard', () => ({ NotificationPreferencesCard: () => null }));
vi.mock('@/components/parent/PremiumRequestsCard', () => ({ PremiumRequestsCard: () => null }));
vi.mock('@/components/parent/MasteryReportCard', () => ({ MasteryReportCard: () => null }));
vi.mock('@/components/parent/PremiumValueCard', () => ({ PremiumValueCard: () => null }));
vi.mock('@/components/parent/DeleteAccountCard', () => ({ DeleteAccountCard: () => null }));
vi.mock('@/components/child/FeedbackDialog', () => ({ FeedbackDialog: () => null }));
vi.mock('@/components/child/ui/Penny', () => ({ Penny: () => null }));
vi.mock('@/hooks/useParentAuthGuard', () => ({ useParentAuthGuard: () => {} }));

const { listChildren } = vi.hoisted(() => ({
  listChildren: vi.fn(),
}));
vi.mock('@/api/parent', () => ({
  parentApi: {
    listChildren: () => listChildren(),
    logout: vi.fn().mockResolvedValue({}),
  },
}));

import ParentDashboard from '../ParentDashboard';

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/parent']}><ParentDashboard /></MemoryRouter>
    </QueryClientProvider>,
  );
}

const ONE_CHILD = [{
  user_id: 'c1', username: 'sam', country_code: 'GB', is_active: true,
  is_premium: false, parent_consent_given_at: null, consent_declined_at: null,
  deleted_at: null, deletion_requested_at: null, age_tier: 'explorer' as const,
  tier_override: null, analytics: null,
}];

describe('ParentDashboard empty state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('shows guidance copy when no children are linked', async () => {
    listChildren.mockResolvedValue([]);
    const { container } = wrap();
    // Wait for data to resolve
    expect(await screen.findByText(/No children linked to this email yet/i)).toBeInTheDocument();
    // The second paragraph contains "make sure your child entered" (text node + <strong> break)
    const ps = container.querySelectorAll('p');
    const guidanceP = Array.from(ps).find((p) => /make sure they entered/i.test(p.textContent ?? ''));
    expect(guidanceP).toBeTruthy();
  });

  it('shows the welcome hint when children are present and hint not dismissed', async () => {
    listChildren.mockResolvedValue(ONE_CHILD);
    wrap();
    expect(await screen.findByText(/Welcome!/i)).toBeInTheDocument();
  });

  it('dismisses the welcome hint on click', async () => {
    listChildren.mockResolvedValue(ONE_CHILD);
    wrap();
    const gotIt = await screen.findByRole('button', { name: /got it/i });
    await userEvent.click(gotIt);
    expect(screen.queryByText(/Welcome!/i)).toBeNull();
    expect(localStorage.getItem('parent-welcome-seen')).toBe('1');
  });

  it('hides the welcome hint when already dismissed', async () => {
    localStorage.setItem('parent-welcome-seen', '1');
    listChildren.mockResolvedValue(ONE_CHILD);
    wrap();
    await screen.findByText(/sam/i);
    expect(screen.queryByText(/Welcome!/i)).toBeNull();
  });
});
