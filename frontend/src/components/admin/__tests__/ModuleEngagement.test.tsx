import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import ModuleEngagement from '../ModuleEngagement';

const base = {
  module_id: 'm1', learners_started: 10, learners_completed: 4,
  completion_rate: 0.4, average_score: 0.82,
  lessons: [
    { lesson_id: 'l1', type: 'card', label: 'Intro', order: 0, views: 10, completions: 9, completion_rate: 0.9, average_score: null, drop_off: 0 },
    { lesson_id: 'l2', type: 'quiz', label: 'What is a stock?', order: 1, views: 9, completions: 4, completion_rate: 0.44, average_score: 0.6, drop_off: 5 },
  ],
};

vi.mock('@/api/admin', () => ({
  useModuleEngagement: () => ({ data: base, isLoading: false, isError: false }),
}));

describe('ModuleEngagement', () => {
  it('renders the summary and per-lesson rows', () => {
    render(<ModuleEngagement moduleId="m1" />);
    expect(screen.getByText(/learners started/i)).toBeInTheDocument();
    expect(screen.getByText('Intro')).toBeInTheDocument();
    expect(screen.getByText('What is a stock?')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<ModuleEngagement moduleId="m1" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
