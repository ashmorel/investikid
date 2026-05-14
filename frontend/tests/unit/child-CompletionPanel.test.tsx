import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { CompletionPanel } from '@/components/child/lesson/CompletionPanel';

const baseResult = { xp_awarded: 25, already_completed: false, total_xp: 320, level: 4, streak_count: 5, practice_available: false };

describe('CompletionPanel', () => {
  it('shows xp awarded, totals, and Next lesson link when next exists', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId="L2" />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Great work/)).toBeInTheDocument();
    expect(screen.getByText(/\+25 XP/)).toBeInTheDocument();
    expect(screen.getByText(/Total: 320 XP/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Next lesson/ })).toHaveAttribute('href', '/lessons/m/L2');
  });

  it('omits Next lesson link and shows Back to module when no next', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={baseResult} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole('link', { name: /Next lesson/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back to module/ })).toHaveAttribute('href', '/lessons/m');
  });

  it('already-completed variant skips XP line and changes heading', () => {
    render(
      <MemoryRouter>
        <CompletionPanel result={{ ...baseResult, already_completed: true, xp_awarded: 0 }} moduleId="m" nextLessonId={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/already done this one/i)).toBeInTheDocument();
    expect(screen.queryByText(/\+0 XP/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\+25 XP/)).not.toBeInTheDocument();
  });
});
