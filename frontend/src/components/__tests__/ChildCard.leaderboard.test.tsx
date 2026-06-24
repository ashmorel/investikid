import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChildCard } from '../ChildCard';
import { parentApi, type Child } from '@/api/parent';

const BASE_CHILD: Child = {
  user_id: 'child-1',
  username: 'alex',
  country_code: 'GB',
  is_active: true,
  is_premium: false,
  parent_consent_given_at: '2026-05-01T10:00:00Z',
  consent_declined_at: null,
  deleted_at: null,
  deletion_requested_at: null,
  age_tier: 'explorer',
  tier_override: null,
  analytics: null,
};

function renderCard(child: Child = BASE_CHILD) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['children'], [child]);
  return render(
    <QueryClientProvider client={qc}>
      <ChildCard child={child} />
    </QueryClientProvider>,
  );
}

describe('ChildCard leaderboard consent toggle', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders an unchecked leaderboard consent switch by default', () => {
    renderCard();
    const sw = screen.getByRole('switch', { name: /show on public leaderboards/i });
    expect(sw).toBeInTheDocument();
    expect(sw).not.toBeChecked();
  });

  it('renders a checked leaderboard consent switch when consent is granted', () => {
    renderCard({ ...BASE_CHILD, leaderboard_consent: true });
    expect(screen.getByRole('switch', { name: /show on public leaderboards/i })).toBeChecked();
  });

  it('toggling ON calls setChildLeaderboardConsent with true', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildLeaderboardConsent')
      .mockResolvedValue(undefined);
    renderCard();
    fireEvent.click(screen.getByRole('switch', { name: /show on public leaderboards/i }));
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith('child-1', true),
    );
  });

  it('toggling OFF calls setChildLeaderboardConsent with false', async () => {
    const spy = vi
      .spyOn(parentApi, 'setChildLeaderboardConsent')
      .mockResolvedValue(undefined);
    renderCard({ ...BASE_CHILD, leaderboard_consent: true });
    fireEvent.click(screen.getByRole('switch', { name: /show on public leaderboards/i }));
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith('child-1', false),
    );
  });

  it('has no axe violations', async () => {
    const { container } = renderCard();
    expect(await axe(container)).toHaveNoViolations();
  });
});
