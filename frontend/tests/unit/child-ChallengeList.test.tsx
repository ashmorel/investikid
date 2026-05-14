import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChallengeList } from '@/components/child/stats/ChallengeList';
import type { ChallengeOut } from '@/api/gamification';

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
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Weekly Learner')).toBeInTheDocument();
    expect(screen.getByText('Market Explorer')).toBeInTheDocument();
  });

  it('shows progress bar with correct aria values for in-progress challenge', () => {
    render(<ChallengeList challenges={challenges} />);
    const bars = screen.getAllByRole('progressbar');
    const inProgress = bars[0];
    expect(inProgress).toHaveAttribute('aria-valuenow', '1');
    expect(inProgress).toHaveAttribute('aria-valuemax', '3');
  });

  it('shows percentage text for in-progress challenge', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('33%')).toBeInTheDocument();
  });

  it('shows XP reward', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('+50 XP')).toBeInTheDocument();
    expect(screen.getByText('+30 XP')).toBeInTheDocument();
  });

  it('shows "Completed!" for completed challenges', () => {
    render(<ChallengeList challenges={challenges} />);
    expect(screen.getByText('Completed!')).toBeInTheDocument();
  });

  it('renders empty state when no challenges', () => {
    render(<ChallengeList challenges={[]} />);
    expect(screen.getByText(/no active challenges this week/i)).toBeInTheDocument();
  });
});
