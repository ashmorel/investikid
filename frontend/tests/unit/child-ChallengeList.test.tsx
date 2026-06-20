import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import { PremiumPaywallProvider } from '@/hooks/usePremiumPaywall';
import type { ChallengeOut } from '@/api/gamification';

function renderWithPaywall(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PremiumPaywallProvider>{ui}</PremiumPaywallProvider>
    </QueryClientProvider>,
  );
}

const challenges: ChallengeOut[] = [
  {
    id: '1', title: 'Weekly Learner', description: 'Complete 3 lessons this week',
    type: 'lessons_completed', target_value: 3, xp_reward: 50,
    starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
    is_premium: false, progress: 1, completed_at: null,
  },
  {
    id: '2', title: 'Market Explorer', description: 'Make 1 paper trade this week',
    type: 'trades_executed', target_value: 1, xp_reward: 30,
    starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
    is_premium: false, progress: 1, completed_at: '2026-05-06T10:00:00Z',
  },
];

describe('ChallengeList', () => {
  it('renders challenge titles', () => {
    renderWithPaywall(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Weekly Learner')).toBeInTheDocument();
    expect(screen.getByText('Market Explorer')).toBeInTheDocument();
  });

  it('shows progress bar with correct aria values for in-progress challenge', () => {
    renderWithPaywall(<ChallengeList challenges={challenges} />);
    const bars = screen.getAllByRole('progressbar');
    const inProgress = bars[0];
    expect(inProgress).toHaveAttribute('aria-valuenow', '1');
    expect(inProgress).toHaveAttribute('aria-valuemax', '3');
  });

  it('shows percentage text for in-progress challenge', () => {
    renderWithPaywall(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('33%')).toBeInTheDocument();
  });

  it('shows XP reward', () => {
    renderWithPaywall(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('+50 XP')).toBeInTheDocument();
    expect(screen.getByText('+30 XP')).toBeInTheDocument();
  });

  it('shows "Completed!" for completed challenges', () => {
    renderWithPaywall(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Completed!')).toBeInTheDocument();
  });

  it('renders empty state when no challenges', () => {
    renderWithPaywall(<ChallengeList challenges={[]} />);
    expect(screen.getByText(/no active challenges this week/i)).toBeInTheDocument();
  });

  it('badges a premium challenge and opens the paywall on tap for non-premium kids', async () => {
    const premiumChallenge: ChallengeOut = {
      id: '3', title: 'Pro Trader', description: 'Premium-only challenge',
      type: 'trades_executed', target_value: 5, xp_reward: 100,
      starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
      is_premium: true, progress: 0, completed_at: null,
    };
    renderWithPaywall(<ChallengeList challenges={[premiumChallenge]} isPremium={false} />);
    expect(screen.getByText('Premium')).toBeInTheDocument();
    await userEvent.click(screen.getByText('Pro Trader'));
    expect(await screen.findByText(/premium unlocks/i)).toBeInTheDocument();
  });

  it('does not lock a premium challenge for premium kids', () => {
    const premiumChallenge: ChallengeOut = {
      id: '3', title: 'Pro Trader', description: 'Premium-only challenge',
      type: 'trades_executed', target_value: 5, xp_reward: 100,
      starts_at: '2026-05-05T00:00:00Z', ends_at: '2026-05-12T00:00:00Z',
      is_premium: true, progress: 0, completed_at: null,
    };
    renderWithPaywall(<ChallengeList challenges={[premiumChallenge]} isPremium={true} />);
    // Still badged, but not a button (no paywall tap target).
    expect(screen.getByText('Premium')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
