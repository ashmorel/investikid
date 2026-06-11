import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { LevelCard } from '../LevelCard';
import type { LevelOut } from '@/api/content';

const base: LevelOut = {
  id: 'l1', module_id: 'm1', title: 'Level 1', order_index: 0, is_premium: false,
  icon: '📊', state: 'in_progress', locked_reason: null, passed: false,
  lessons_total: 4, lessons_completed: 1,
};

describe('LevelCard', () => {
  it('unlocked level is clickable', () => {
    const onOpen = vi.fn();
    render(<LevelCard level={base} onOpen={onOpen} onLockedClick={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /Level 1/ }));
    expect(onOpen).toHaveBeenCalled();
  });

  it('premium-locked shows premium and calls onLockedClick', () => {
    const onLockedClick = vi.fn();
    render(<LevelCard level={{ ...base, state: 'locked', locked_reason: 'premium' }}
      onOpen={() => {}} onLockedClick={onLockedClick} />);
    expect(screen.getByText(/Premium/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(onLockedClick).toHaveBeenCalled();
  });

  it('premium-locked shows the PremiumBadge and an unlock teaser', () => {
    render(<LevelCard level={{ ...base, state: 'locked', locked_reason: 'premium' }}
      onOpen={() => {}} onLockedClick={() => {}} />);
    expect(screen.getByText('Premium')).toBeInTheDocument();
    expect(screen.getByText(/unlock to continue/i)).toBeInTheDocument();
  });

  it('progression-locked shows unlock hint', () => {
    render(<LevelCard level={{ ...base, state: 'locked', locked_reason: 'progression' }}
      onOpen={() => {}} onLockedClick={() => {}} />);
    expect(screen.getByText(/unlock/i)).toBeInTheDocument();
  });

  it('shows a Mastered stamp with the formatted date when mastered_at is set', () => {
    render(<LevelCard
      level={{ ...base, state: 'completed', passed: true, mastered_at: '2026-06-11T09:30:00Z' }}
      onOpen={() => {}} onLockedClick={() => {}} />);
    expect(screen.getByText(/Mastered/)).toBeInTheDocument();
    expect(screen.getByText(/11 Jun 2026/)).toBeInTheDocument();
  });

  it('does not show a Mastered stamp when mastered_at is null', () => {
    render(<LevelCard level={{ ...base, mastered_at: null }} onOpen={() => {}} onLockedClick={() => {}} />);
    expect(screen.queryByText(/Mastered/)).not.toBeInTheDocument();
  });

  it('has no axe violations with the Mastered stamp', async () => {
    const { container } = render(<LevelCard
      level={{ ...base, state: 'completed', passed: true, mastered_at: '2026-06-11T09:30:00Z' }}
      onOpen={() => {}} onLockedClick={() => {}} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
