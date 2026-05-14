import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BadgeGrid } from '@/components/child/stats/BadgeGrid';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

const allBadges: BadgeDefinition[] = [
  { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 1, earned_at: null },
  { id: '2', name: 'Streak Master', description: 'Maintain a 7-day streak', icon_url: '/x.svg', condition_type: 'streak_days', condition_value: 7, earned_at: null },
  { id: '3', name: 'First Trade', description: 'Execute your first paper trade', icon_url: '/x.svg', condition_type: 'trade_count', condition_value: 1, earned_at: null },
  { id: '4', name: 'Century Club', description: 'Earn 100 XP', icon_url: '/x.svg', condition_type: 'total_xp', condition_value: 100, earned_at: null },
  { id: '5', name: 'Quiz Ace', description: 'Complete 10 lessons', icon_url: '/x.svg', condition_type: 'lesson_count', condition_value: 10, earned_at: null },
];

const earnedBadges: EarnedBadge[] = [
  { id: '1', name: 'First Step', description: 'Complete your first lesson', icon_url: '/x.svg', earned_at: '2026-05-01T10:00:00Z' },
  { id: '4', name: 'Century Club', description: 'Earn 100 XP', icon_url: '/x.svg', earned_at: '2026-05-03T14:00:00Z' },
];

describe('BadgeGrid', () => {
  it('renders all 5 badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('First Step')).toBeInTheDocument();
    expect(screen.getByText('Streak Master')).toBeInTheDocument();
    expect(screen.getByText('First Trade')).toBeInTheDocument();
    expect(screen.getByText('Century Club')).toBeInTheDocument();
    expect(screen.getByText('Quiz Ace')).toBeInTheDocument();
  });

  it('shows earned badges with "Earned" text', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    const earnedTexts = screen.getAllByText(/^Earned/);
    expect(earnedTexts).toHaveLength(2);
  });

  it('shows lock icon for locked badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    const lockIcons = screen.getAllByLabelText(/locked/i);
    expect(lockIcons).toHaveLength(3);
  });

  it('shows condition text as description for locked badges', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('Maintain a 7-day streak')).toBeInTheDocument();
    expect(screen.getByText('Execute your first paper trade')).toBeInTheDocument();
  });

  it('renders earned badge description', () => {
    render(<BadgeGrid allBadges={allBadges} earnedBadges={earnedBadges} />);
    expect(screen.getByText('Complete your first lesson')).toBeInTheDocument();
  });
});
