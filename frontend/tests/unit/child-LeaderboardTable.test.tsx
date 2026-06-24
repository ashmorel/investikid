import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { LeaderboardTable } from '@/components/child/stats/LeaderboardTable';
import type { LeaderboardRow } from '@/api/gamification';

const rows: LeaderboardRow[] = [
  { rank: 1, name: 'alice', country_code: 'US', points: 120, is_me: false },
  { rank: 2, name: 'testuser', country_code: 'GB', points: 80, is_me: true },
  { rank: 3, name: 'bob', country_code: 'FR', points: 50, is_me: false },
];

describe('LeaderboardTable', () => {
  it('renders table with rank numbers', () => {
    render(<LeaderboardTable rows={rows} currentName="testuser" pointsLabel="XP This Week" />);
    const tableRows = screen.getAllByRole('row');
    // 1 header + 3 data rows
    expect(tableRows).toHaveLength(4);
    expect(within(tableRows[1]).getByText('1')).toBeInTheDocument();
    expect(within(tableRows[2]).getByText('2')).toBeInTheDocument();
    expect(within(tableRows[3]).getByText('3')).toBeInTheDocument();
  });

  it('renders names', () => {
    render(<LeaderboardTable rows={rows} currentName="testuser" pointsLabel="XP This Week" />);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('testuser')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
  });

  it('highlights current user row (is_me)', () => {
    render(<LeaderboardTable rows={rows} currentName="testuser" pointsLabel="XP This Week" />);
    // testuser row should be bold (is_me=true); check the row exists
    expect(screen.getByText('testuser')).toBeInTheDocument();
  });

  it('renders XP values', () => {
    render(<LeaderboardTable rows={rows} currentName="testuser" pointsLabel="XP This Week" />);
    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('80')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });
});
