import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';

vi.mock('canvas-confetti', () => ({ default: vi.fn() }));

const baseResult = { xp_awarded: 25, already_completed: false, total_xp: 320, level: 4, streak_count: 5, practice_available: false };

describe('CompletionPanel', () => {
  it('shows xp awarded, totals, and Next Quest link when next exists', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId="L2" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Quest Complete!/)).toBeInTheDocument();
    expect(screen.getByText(/Total: 320 XP/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Next Quest/ })).toHaveAttribute('href', '/lessons/m/L2');
  });

  it('omits Next Quest link and shows Back to module when no next', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: /Next Quest/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to module/ })).toHaveAttribute('href', '/lessons/m');
  });

  it('already-completed variant skips XP line and changes heading', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/already done this one/i)).toBeInTheDocument();
  });

  it('fires confetti when quest is freshly completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(confetti).toHaveBeenCalled();
  });

  it('does not fire confetti when already completed', async () => {
    const confetti = (await import('canvas-confetti')).default;
    (confetti as ReturnType<typeof vi.fn>).mockClear();
    render(
      <MemoryRouter>
        <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(confetti).not.toHaveBeenCalled();
  });
});
