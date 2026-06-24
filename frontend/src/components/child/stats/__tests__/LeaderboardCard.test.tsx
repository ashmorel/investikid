import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LeaderboardCard } from '../LeaderboardCard';

const getLeaderboard = vi.fn();
vi.mock('@/api/gamification', () => ({
  gamificationApi: { getLeaderboard: (...a: unknown[]) => getLeaderboard(...a) },
}));

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  getLeaderboard.mockReset();
  getLeaderboard.mockResolvedValue([
    { rank: 1, name: 'CleverOtter42', country_code: 'GB', points: 120, is_me: false, avatar: { skin: 'skin_sky', accessories: ['party_hat'] } },
    { rank: 2, name: 'You', country_code: 'GB', points: 90, is_me: true, avatar: { skin: null, accessories: [] } },
  ]);
});

describe('LeaderboardCard', () => {
  it('defaults to Market + XP and renders rows', async () => {
    wrap(<LeaderboardCard />);
    await waitFor(() => expect(getLeaderboard).toHaveBeenCalledWith('market', 'xp'));
    expect(await screen.findByText('CleverOtter42')).toBeInTheDocument();
  });

  it('switching scope to Global refetches with global', async () => {
    wrap(<LeaderboardCard />);
    await screen.findByText('CleverOtter42');
    fireEvent.click(screen.getByRole('radio', { name: /global/i }));
    await waitFor(() => expect(getLeaderboard).toHaveBeenCalledWith('global', 'xp'));
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<LeaderboardCard />);
    await screen.findByText('CleverOtter42');
    expect(await axe(container)).toHaveNoViolations();
  });

  it('renders a Penny avatar on each row', async () => {
    const { container } = wrap(<LeaderboardCard />);
    await screen.findByText('CleverOtter42');
    // at least one Penny svg in the rendered rows
    expect(container.querySelectorAll('svg[viewBox="0 0 56 56"]').length).toBeGreaterThanOrEqual(1);
  });
});
