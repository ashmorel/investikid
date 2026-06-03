import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import HomeHero from '../HomeHero';

const next = {
  mode: 'start' as const, moduleId: 'm1', levelId: 'l1', lessonId: 'q1',
  moduleTitle: 'Stocks', moduleIcon: '📈', lessonLabel: 'What is a Stock?',
  to: '/lessons/m1/l1/q1', isLoading: false,
};

vi.mock('@/hooks/useNextLesson', () => ({ useNextLesson: () => next }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false } }) }));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
  useHomeGreeting: () => ({ data: undefined }),
}));
vi.mock('@/hooks/useProgress', () => ({ useProgress: () => ({ data: { streak_count: 0 } }) }));

function wrap(ui: React.ReactNode) { return <MemoryRouter>{ui}</MemoryRouter>; }

describe('HomeHero', () => {
  it('shows the templated greeting, lesson title and a Start link', () => {
    render(wrap(<HomeHero />));
    expect(screen.getByText(/start your money journey/i)).toBeInTheDocument();
    expect(screen.getByText('What is a Stock?')).toBeInTheDocument();
    const cta = screen.getByRole('link', { name: /start/i });
    expect(cta).toHaveAttribute('href', '/lessons/m1/l1/q1');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<HomeHero />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
