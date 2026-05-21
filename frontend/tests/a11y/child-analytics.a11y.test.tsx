import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { ChildAnalytics } from '@/components/ChildAnalytics';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

const ANALYTICS: ChildAnalyticsType = {
  level: 5,
  xp: 480,
  xp_to_next_level: 20,
  streak_count: 3,
  lessons_completed: 12,
  lessons_total: 30,
  recent_lessons: [
    { title: 'What is a Stock?', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
    { title: 'Supply & Demand', type: 'quiz', score: 0.9, completed_at: '2026-05-19T10:00:00Z' },
  ],
  badges: [
    { name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' },
  ],
};

describe('a11y: ChildAnalytics', () => {
  it('collapsed state has no axe violations', async () => {
    const { container } = render(<ChildAnalytics analytics={ANALYTICS} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('expanded state has no axe violations', async () => {
    const user = userEvent.setup();
    const { container } = render(<ChildAnalytics analytics={ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(await axe(container)).toHaveNoViolations();
  });

  it('toggle is keyboard accessible', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    toggle.focus();
    await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: /hide progress/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('progress bar has correct role and aria attributes', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '12');
    expect(bar).toHaveAttribute('aria-valuemax', '30');
  });
});
