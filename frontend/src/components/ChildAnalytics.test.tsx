import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChildAnalytics } from './ChildAnalytics';
import type { ChildAnalytics as ChildAnalyticsType } from '@/api/parent';

const MOCK_ANALYTICS: ChildAnalyticsType = {
  level: 5,
  xp: 480,
  xp_to_next_level: 20,
  streak_count: 3,
  lessons_completed: 12,
  lessons_total: 30,
  recent_lessons: [
    { title: 'What is a Stock?', type: 'card', score: null, completed_at: '2026-05-20T10:00:00Z' },
    { title: 'Supply & Demand', type: 'quiz', score: 0.9, completed_at: '2026-05-19T10:00:00Z' },
    { title: 'Reading Graphs', type: 'quiz', score: 0.6, completed_at: '2026-05-18T10:00:00Z' },
  ],
  badges: [
    { name: 'First Lesson', icon: 'trophy', earned_at: '2026-05-15T10:00:00Z' },
    { name: 'Stock Savvy', icon: 'chart', earned_at: '2026-05-18T10:00:00Z' },
  ],
};

const EMPTY_ANALYTICS: ChildAnalyticsType = {
  level: 1,
  xp: 0,
  xp_to_next_level: 100,
  streak_count: 0,
  lessons_completed: 0,
  lessons_total: 30,
  recent_lessons: [],
  badges: [],
};

describe('ChildAnalytics', () => {
  it('renders summary line with level, xp, and streak', () => {
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    expect(screen.getByText(/Lvl 5/)).toBeInTheDocument();
    expect(screen.getByText(/480 XP/)).toBeInTheDocument();
    expect(screen.getByText(/3-day streak/)).toBeInTheDocument();
  });

  it('does not show expanded content by default', () => {
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    expect(screen.queryByText(/12 of 30 lessons/)).not.toBeInTheDocument();
  });

  it('expands on toggle click to show progress and lessons', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText(/12 of 30 lessons/)).toBeInTheDocument();
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    expect(screen.getByText('Supply & Demand')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
  });

  it('shows badges in expanded section', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText(/First Lesson/)).toBeInTheDocument();
    expect(screen.getByText(/Stock Savvy/)).toBeInTheDocument();
  });

  it('collapses on second toggle click', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    await user.click(toggle);
    expect(screen.getByText(/12 of 30 lessons/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /hide progress/i }));
    expect(screen.queryByText(/12 of 30 lessons/)).not.toBeInTheDocument();
  });

  it('shows zero-state message when no activity', () => {
    render(<ChildAnalytics analytics={EMPTY_ANALYTICS} />);
    expect(screen.getByText(/No activity yet/)).toBeInTheDocument();
  });

  it('toggle has aria-expanded attribute', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    const toggle = screen.getByRole('button', { name: /show progress/i });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await user.click(toggle);
    expect(screen.getByRole('button', { name: /hide progress/i })).toHaveAttribute('aria-expanded', 'true');
  });

  it('shows checkmark for card lessons, percentage for quizzes', async () => {
    const user = userEvent.setup();
    render(<ChildAnalytics analytics={MOCK_ANALYTICS} />);
    await user.click(screen.getByRole('button', { name: /show progress/i }));
    expect(screen.getByText('✓')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('60%')).toBeInTheDocument();
  });
});
