import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

let mockTier: 'explorer' | 'investor' = 'explorer';
vi.mock('@/lib/ageTier', async (importOriginal) => {
  const orig = await importOriginal<typeof import('@/lib/ageTier')>();
  return { ...orig, useAgeTier: () => mockTier };
});

import { StatsCard } from '../StatsCard';

const props = { xp: 1250, level: 4, streakCount: 5, streakFreezes: 1, lastActivityDate: '2026-06-12', today: new Date('2026-06-12T12:00:00') };

describe('StatsCard', () => {
  beforeEach(() => { mockTier = 'explorer'; });
  it('shows level, streak, freezes and XP progress', () => {
    render(<StatsCard {...props} />);
    expect(screen.getByText(/Level 4/)).toBeInTheDocument();
    expect(screen.getByText(/5-day streak/)).toBeInTheDocument();
    expect(screen.getByLabelText(/streak freeze/)).toBeInTheDocument();
    // The progressbar is now the DAILY GOAL bar (m7); level progress lives in the caption.
    const bar = screen.getByRole('progressbar', { name: /daily goal/i });
    expect(bar).toHaveAttribute('aria-valuemax', '30');
    expect(screen.getByText(/50 XP to Level 5/)).toBeInTheDocument();
  });
  it('marks streak inactive when last activity is stale', () => {
    render(<StatsCard {...props} lastActivityDate="2026-06-01" />);
    expect(screen.getByLabelText('streak inactive')).toBeInTheDocument();
  });
  it('hides freezes when zero', () => {
    render(<StatsCard {...props} streakFreezes={0} />);
    expect(screen.queryByLabelText(/streak freeze/)).toBeNull();
  });
  it('shows "next freeze in N days" when nextFreezeIn is given on an active streak', () => {
    render(<StatsCard {...props} nextFreezeIn={3} />);
    expect(screen.getByText(/next freeze in 3 days/i)).toBeInTheDocument();
  });
  it('omits the next-freeze hint when nextFreezeIn is zero / undefined', () => {
    const { rerender } = render(<StatsCard {...props} />);
    expect(screen.queryByText(/next freeze in/i)).toBeNull();
    rerender(<StatsCard {...props} nextFreezeIn={0} />);
    expect(screen.queryByText(/next freeze in/i)).toBeNull();
  });
  it('omits the next-freeze hint when the streak is inactive', () => {
    render(<StatsCard {...props} lastActivityDate="2026-06-01" nextFreezeIn={3} />);
    expect(screen.queryByText(/next freeze in/i)).toBeNull();
  });
  it('investor tier renders without emoji', () => {
    mockTier = 'investor';
    const { container } = render(<StatsCard {...props} />);
    expect(container.textContent).not.toMatch(/[⭐🔥🛡]/u);
    expect(screen.getByText(/Level 4/)).toBeInTheDocument();
    expect(screen.getByText(/1 freeze/)).toBeInTheDocument();
  });
  it('has no axe violations', async () => {
    const { container } = render(<StatsCard {...props} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
