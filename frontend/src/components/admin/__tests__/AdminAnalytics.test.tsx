import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { AnalyticsSummary } from '@/api/admin';
import AdminAnalytics from '../AdminAnalytics';

const summary: AnalyticsSummary = {
  window_days: 30,
  activation: { signups: 10, activated: 6, rate_pct: 60.0 },
  cohorts: [
    { week_start: '2026-06-01', signups: 5, d7_pct: 40.0, d30_pct: null },
  ],
  funnel: { paywall_view: 12, trial_started: 3, subscription_activated: 2 },
  engagement: {
    home_view: 100,
    home_cta_tap: 55,
    cta_through_pct: 55.0,
    quicklink_taps: { portfolio: 7, review: 4 },
    lesson_completed: 80,
    digest_sent: 9,
  },
};

const useAnalyticsSummary = vi.fn((_days: number) => ({ data: summary, isLoading: false, isError: false }));
vi.mock('@/api/admin', () => ({
  useAnalyticsSummary: (days: number) => useAnalyticsSummary(days),
}));

describe('AdminAnalytics', () => {
  it('renders KPI cards, funnel, cohorts and shortcut taps', () => {
    render(<AdminAnalytics />);
    expect(screen.getByText('60%')).toBeInTheDocument(); // activation
    expect(screen.getByText('55%')).toBeInTheDocument(); // tap-through
    expect(screen.getByText('Trials started')).toBeInTheDocument();
    expect(screen.getByText('2026-06-01')).toBeInTheDocument();
    expect(screen.getByText('portfolio')).toBeInTheDocument();
  });

  it('switches the range and refetches', () => {
    render(<AdminAnalytics />);
    fireEvent.click(screen.getByRole('button', { name: '7d' }));
    expect(useAnalyticsSummary).toHaveBeenLastCalledWith(7);
    expect(screen.getByRole('button', { name: '7d' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('shows an error state', () => {
    useAnalyticsSummary.mockReturnValueOnce({
      data: undefined as unknown as AnalyticsSummary,
      isLoading: false,
      isError: true,
    });
    render(<AdminAnalytics />);
    expect(screen.getByRole('alert')).toHaveTextContent(/could not load/i);
  });

  it('has no axe violations', async () => {
    const { container } = render(<AdminAnalytics />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
