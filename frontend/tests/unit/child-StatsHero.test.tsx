import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatsHero } from '@/components/child/stats/StatsHero';

function renderHero(overrides: Partial<Parameters<typeof StatsHero>[0]> = {}) {
  const defaults = {
    xp: 250,
    streakCount: 5,
    lastActivityDate: '2026-05-08',
    badgeCount: 4,
    challengeCount: 2,
    today: new Date('2026-05-08T12:00:00Z'),
  };
  return render(<StatsHero {...defaults} {...overrides} />);
}

describe('StatsHero', () => {
  it('renders correct level from XP (250 XP = Level 3)', () => {
    renderHero();
    expect(screen.getByText(/Level 3/)).toBeInTheDocument();
  });

  it('renders total XP as its own node', () => {
    renderHero();
    expect(screen.getByText('250')).toBeInTheDocument();
  });

  it('renders the level-progress bar (250 % 100 = 50%)', () => {
    renderHero();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('renders the streak count', () => {
    renderHero();
    expect(screen.getByText(/5-day/)).toBeInTheDocument();
  });

  it('shows active streak state when activity is recent', () => {
    renderHero({ lastActivityDate: '2026-05-08', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak active/i)).toBeInTheDocument();
  });

  it('shows inactive streak state when activity is old', () => {
    renderHero({ lastActivityDate: '2026-05-01', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak inactive/i)).toBeInTheDocument();
  });

  it('renders badge and challenge chips from the counts', () => {
    renderHero();
    expect(screen.getByText(/4 badges/)).toBeInTheDocument();
    expect(screen.getByText(/2 challenges/)).toBeInTheDocument();
  });

  it('handles 0 XP (Level 1, 0% progress)', () => {
    renderHero({ xp: 0 });
    expect(screen.getByText(/Level 1/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  });
});
