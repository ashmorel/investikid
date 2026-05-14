import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { XpSummary } from '@/components/child/stats/XpSummary';

function renderSummary(overrides: Partial<Parameters<typeof XpSummary>[0]> = {}) {
  const defaults = {
    xp: 250,
    streakCount: 5,
    lastActivityDate: '2026-05-08',
    today: new Date('2026-05-08T12:00:00Z'),
  };
  return render(<XpSummary {...defaults} {...overrides} />);
}

describe('XpSummary', () => {
  it('renders correct level from XP (250 XP = Level 3)', () => {
    renderSummary();
    expect(screen.getByText(/Level 3/)).toBeInTheDocument();
  });

  it('renders total XP', () => {
    renderSummary();
    expect(screen.getByText('250')).toBeInTheDocument();
  });

  it('renders progress bar with correct width (250 % 100 = 50%)', () => {
    renderSummary();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });

  it('renders streak count', () => {
    renderSummary();
    expect(screen.getByText(/5-day/)).toBeInTheDocument();
  });

  it('shows active streak state when activity is recent', () => {
    renderSummary({ lastActivityDate: '2026-05-08', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak active/i)).toBeInTheDocument();
  });

  it('shows inactive streak state when activity is old', () => {
    renderSummary({ lastActivityDate: '2026-05-01', today: new Date('2026-05-08T12:00:00Z') });
    expect(screen.getByLabelText(/streak inactive/i)).toBeInTheDocument();
  });

  it('handles 0 XP (Level 1, 0% progress)', () => {
    renderSummary({ xp: 0 });
    expect(screen.getByText(/Level 1/)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '0');
  });
});
