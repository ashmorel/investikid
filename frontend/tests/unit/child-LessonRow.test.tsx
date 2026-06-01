import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LessonRow } from '@/components/child/LessonRow';

const completedLesson = { id: 'L1', type: 'card' as const, title: 'A', xp_reward: 10, order_index: 0, completed: true };
const nextLesson = { id: 'L2', type: 'quiz' as const, title: 'B', xp_reward: 25, order_index: 1, completed: false };
const laterLesson = { id: 'L3', type: 'scenario' as const, title: 'C', xp_reward: 20, order_index: 2, completed: false };

describe('LessonRow', () => {
  it('renders title, type, xp, and completed icon', () => {
    render(<MemoryRouter><LessonRow moduleId="m" lesson={completedLesson} status="done" /></MemoryRouter>);
    expect(screen.getByText(/1\. A/)).toBeInTheDocument();
    expect(screen.getByText(/Card/i)).toBeInTheDocument();
    expect(screen.getByText(/10 XP/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/completed/i)).toBeInTheDocument();
  });

  it('renders next-up icon for next lesson', () => {
    render(<MemoryRouter><LessonRow moduleId="m" lesson={nextLesson} status="next" /></MemoryRouter>);
    expect(screen.getByLabelText(/next up/i)).toBeInTheDocument();
  });

  it('renders later icon for not-yet-started lessons', () => {
    render(<MemoryRouter><LessonRow moduleId="m" lesson={laterLesson} status="later" /></MemoryRouter>);
    expect(screen.getByLabelText(/not started/i)).toBeInTheDocument();
  });

  it('row without levelId links to /lessons/:moduleId/:lessonId (legacy 2-segment)', () => {
    render(<MemoryRouter><LessonRow moduleId="mod-x" lesson={nextLesson} status="next" /></MemoryRouter>);
    expect(screen.getByRole('link')).toHaveAttribute('href', '/lessons/mod-x/L2');
  });

  it('row with levelId links to /lessons/:moduleId/:levelId/:lessonId (3-segment)', () => {
    render(<MemoryRouter><LessonRow moduleId="mod-x" levelId="lv-1" lesson={nextLesson} status="next" /></MemoryRouter>);
    expect(screen.getByRole('link')).toHaveAttribute('href', '/lessons/mod-x/lv-1/L2');
  });
});
