import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { LeaderboardTable } from '@/components/child/stats/LeaderboardTable';
import type { LeaderboardEntry } from '@/api/gamification';

const entries: LeaderboardEntry[] = [
  { username: 'alice', country_code: 'US', xp_this_week: 120 },
  { username: 'testuser', country_code: 'GB', xp_this_week: 80 },
  { username: 'bob', country_code: 'FR', xp_this_week: 50 },
];

describe('LeaderboardTable', () => {
  it('renders table with rank numbers', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    const rows = screen.getAllByRole('row');
    // 1 header + 3 data rows
    expect(rows).toHaveLength(4);
    expect(within(rows[1]).getByText('1')).toBeInTheDocument();
    expect(within(rows[2]).getByText('2')).toBeInTheDocument();
    expect(within(rows[3]).getByText('3')).toBeInTheDocument();
  });

  it('renders usernames', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('testuser')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
  });

  it('highlights current user row with "You" badge', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('You')).toBeInTheDocument();
  });

  it('renders country flag with aria-label', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByLabelText('US')).toBeInTheDocument();
    expect(screen.getByLabelText('GB')).toBeInTheDocument();
    expect(screen.getByLabelText('FR')).toBeInTheDocument();
  });

  it('renders XP values', () => {
    render(<LeaderboardTable entries={entries} currentUsername="testuser" />);
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('80')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('renders empty state when no entries', () => {
    render(<LeaderboardTable entries={[]} currentUsername="testuser" />);
    expect(screen.getByText(/no activity this week/i)).toBeInTheDocument();
  });
});
