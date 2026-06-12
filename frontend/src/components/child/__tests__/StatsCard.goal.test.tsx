import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

let mockTier: 'explorer' | 'investor' = 'explorer';
vi.mock('@/lib/ageTier', async (importOriginal) => {
  const orig = await importOriginal<typeof import('@/lib/ageTier')>();
  return { ...orig, useAgeTier: () => mockTier };
});

import { StatsCard } from '../StatsCard';

const props = {
  xp: 1250, level: 4, streakCount: 5, streakFreezes: 0,
  lastActivityDate: '2026-06-12', today: new Date('2026-06-12T12:00:00'),
};

describe('StatsCard daily goal (m7)', () => {
  beforeEach(() => { mockTier = 'explorer'; });

  it('shows progress towards the goal', () => {
    render(<StatsCard {...props} dailyGoalXp={30} xpToday={20} />);
    expect(screen.getByText(/today: 20 \/ 30 xp/i)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar', { name: /daily goal/i });
    expect(bar).toHaveAttribute('aria-valuenow', '20');
    expect(bar).toHaveAttribute('aria-valuemax', '30');
    expect(screen.queryByText(/goal met/i)).toBeNull();
  });

  it('celebrates when the goal is met (explorer emoji)', () => {
    render(<StatsCard {...props} dailyGoalXp={30} xpToday={35} />);
    expect(screen.getByText(/goal met! ⭐/i)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar', { name: /daily goal/i });
    expect(bar).toHaveAttribute('aria-valuenow', '30'); // clamped
  });

  it('investor tier celebrates without emoji', () => {
    mockTier = 'investor';
    render(<StatsCard {...props} dailyGoalXp={10} xpToday={10} />);
    expect(screen.getByText(/^goal met$/i)).toBeInTheDocument();
  });

  it('keeps the level caption', () => {
    render(<StatsCard {...props} dailyGoalXp={30} xpToday={0} />);
    expect(screen.getByText(/50 XP to Level 5/)).toBeInTheDocument();
  });

  it('has no axe violations in met state', async () => {
    const { container } = render(<StatsCard {...props} dailyGoalXp={10} xpToday={15} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
