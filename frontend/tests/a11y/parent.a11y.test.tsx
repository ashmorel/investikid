import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';

import ParentDashboard from '@/pages/ParentDashboard';

vi.mock('@/api/billing', () => ({
  billingApi: {
    getStatus: vi.fn().mockResolvedValue({
      has_subscription: false,
      status: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
    }),
    createCheckout: vi.fn(),
    createPortal: vi.fn(),
  },
}));

// Prevent SignInMethods from making real fetch calls during a11y tests
vi.mock('@/api/parentAuth', () => ({
  parentAuthApi: {
    listIdentities: vi.fn().mockResolvedValue([]),
    linkProvider: vi.fn(),
    unlinkProvider: vi.fn(),
  },
}));
vi.mock('@/lib/socialLogin', () => ({ socialIdToken: vi.fn() }));

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
    // Fresh Response per call: body is single-use, and several queries fetch.
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      const body = url.includes('/parent/mastery-report')
        ? { window_days: 30, children: [], household_mastered_count: 0 }
        : [];
      return new Response(JSON.stringify(body), { status: 200 }) as never;
    });
    const { container } = wrap(<ParentDashboard />);
    await waitFor(() => expect(screen.getByText(/No children linked/i)).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });

  it('ParentDashboard with children has no axe violations', async () => {
    const children = [
          {
            user_id: 'u1', username: 'kid1', country_code: 'GB', is_active: true,
            parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
            deleted_at: null, deletion_requested_at: null,
            is_premium: false,
            analytics: {
              level: 3, xp: 250, xp_to_next_level: 250, streak_count: 2,
              lessons_completed: 5, lessons_total: 20,
              recent_lessons: [
                { title: 'Test Lesson', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
              ],
              badges: [{ name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' }],
            },
          },
          {
            user_id: 'u2', username: 'kid2', country_code: 'US', is_active: true,
            parent_consent_given_at: '2026-01-01T00:00:00Z', consent_declined_at: null,
            deleted_at: null, deletion_requested_at: null,
            is_premium: false,
            analytics: {
              level: 3, xp: 250, xp_to_next_level: 250, streak_count: 2,
              lessons_completed: 5, lessons_total: 20,
              recent_lessons: [
                { title: 'Test Lesson', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
              ],
              badges: [{ name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' }],
            },
          },
    ];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      const body = url.includes('/parent/groups')
        ? []
        : url.includes('/parent/mastery-report')
          ? {
              window_days: 30,
              household_mastered_count: 1,
              children: [{
                user_id: 'u1', username: 'kid1', mastered_count: 1, mastered_total: 2,
                objectives: ['explain what a stock is'], standards: [{ framework: 'MaPS', code: 'MM-1' }],
                weak_topic: 'budgeting',
                next_recommendation: { module_title: 'Budgeting Basics', level_title: 'Level 1' },
              }],
            }
          : children;
      return new Response(JSON.stringify(body), { status: 200 }) as never;
    });
    const { container } = wrap(<ParentDashboard />);
    await waitFor(() => expect(screen.getByRole('heading', { name: 'kid1' })).toBeInTheDocument());
    expect(await axe(container)).toHaveNoViolations();
  });
});
