import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';

vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

const baseResult = { xp_awarded: 25, already_completed: false, total_xp: 320, level: 4, streak_count: 5, practice_available: false };

describe('CompletionPanel', () => {
  it('shows xp awarded and totals', () => {
    const onContinue = vi.fn();
    render(<CompletionPanel result={baseResult} onContinue={onContinue} />);
    expect(screen.getByText(/Quest Complete!/)).toBeInTheDocument();
    expect(screen.getByText(/Total: 320 XP/)).toBeInTheDocument();
  });

  it('calls onContinue when Continue button is clicked', () => {
    const onContinue = vi.fn();
    render(<CompletionPanel result={baseResult} onContinue={onContinue} />);
    fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    expect(onContinue).toHaveBeenCalledOnce();
  });

  it('already-completed variant skips XP line and changes heading', () => {
    const onContinue = vi.fn();
    render(
      <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} onContinue={onContinue} />,
    );
    expect(screen.getByText(/already done this one/i)).toBeInTheDocument();
  });

  it('fires confetti when quest is freshly completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    const onContinue = vi.fn();
    render(<CompletionPanel result={baseResult} onContinue={onContinue} />);
    expect(confetti).toHaveBeenCalled();
  });

  it('does not fire confetti when already completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    (confetti as unknown as ReturnType<typeof vi.fn>).mockClear();
    const onContinue = vi.fn();
    render(
      <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} onContinue={onContinue} />,
    );
    expect(confetti).not.toHaveBeenCalled();
  });
});
