import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { AchievementsStrip } from '../AchievementsStrip';
import type { BadgeDefinition, EarnedBadge } from '@/api/gamification';

const all: BadgeDefinition[] = [
  { id: 'b1', name: 'First Steps', description: '', icon_url: '👣', condition_type: 'lessons_completed', condition_value: 1, earned_at: null },
  { id: 'b2', name: 'On Fire', description: '', icon_url: '🔥', condition_type: 'streak', condition_value: 5, earned_at: null },
];
const earned: EarnedBadge[] = [{ id: 'b1', name: 'First Steps', description: '', icon_url: '👣', earned_at: '2026-01-01' }];

function wrap(ui: React.ReactNode) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('AchievementsStrip', () => {
  it('renders all badge names and a See all link to /stats', () => {
    wrap(<AchievementsStrip allBadges={all} earnedBadges={earned} />);
    expect(screen.getByText('First Steps')).toBeInTheDocument();
    expect(screen.getByText('On Fire')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /see all/i })).toHaveAttribute('href', '/stats');
  });

  it('renders nothing when there are no badges', () => {
    const { container } = wrap(<AchievementsStrip allBadges={[]} earnedBadges={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('has no axe violations', async () => {
    const { container } = wrap(<AchievementsStrip allBadges={all} earnedBadges={earned} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
