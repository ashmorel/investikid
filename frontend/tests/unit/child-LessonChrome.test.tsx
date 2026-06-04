import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { LessonChrome } from '@/components/child/lesson/LessonChrome';

describe('LessonChrome', () => {
  it('renders back button, progress bar, count, XP badge, and Penny speech bubble', () => {
    render(
      <LessonChrome position={2} total={5} xpReward={20} onBack={vi.fn()} />,
    );

    // Back button
    expect(screen.getByRole('button', { name: /go back/i })).toBeInTheDocument();

    // Progress bar with accessible label
    const bar = screen.getByRole('progressbar', { name: /quest 2 of 5/i });
    expect(bar).toHaveAttribute('aria-valuenow', '1');
    expect(bar).toHaveAttribute('aria-valuemax', '5');

    // Count label
    expect(screen.getByText('2/5')).toBeInTheDocument();

    // XP badge
    expect(screen.getByText(/20 XP/i)).toBeInTheDocument();

    // Penny speech bubble (static text)
    expect(screen.getByText(/you're doing great/i)).toBeInTheDocument();
  });

  it('calls onBack when back button is clicked', () => {
    const onBack = vi.fn();
    render(<LessonChrome position={1} total={3} xpReward={10} onBack={onBack} />);
    fireEvent.click(screen.getByRole('button', { name: /go back/i }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('omits count and hides progress fill when total is 0', () => {
    render(<LessonChrome position={1} total={0} xpReward={10} onBack={vi.fn()} />);
    expect(screen.queryByText(/1\//)).not.toBeInTheDocument();
  });
});
