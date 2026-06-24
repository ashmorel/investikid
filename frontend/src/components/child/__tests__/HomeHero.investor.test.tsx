import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/api/cosmetics', () => ({
  useEquippedCosmetics: () => ({ accessories: [], skin: null, background: null }),
}));
import { MemoryRouter } from 'react-router-dom';
import HomeHero from '../HomeHero';

const next = {
  mode: 'continue' as const, moduleId: 'm1', levelId: 'l1', lessonId: 'q1',
  moduleTitle: 'Stocks', moduleIcon: '📈', lessonLabel: 'What is a Stock?',
  to: '/lessons/m1/l1/q1', isLoading: false,
};
vi.mock('@/hooks/useNextLesson', () => ({ useNextLesson: () => next }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false, age_tier: 'investor' } }) }));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
  useHomeGreeting: () => ({ data: undefined }),
}));
vi.mock('@/hooks/useProgress', () => ({ useProgress: () => ({ data: { streak_count: 0 } }) }));

function wrap(ui: React.ReactNode) { return <MemoryRouter>{ui}</MemoryRouter>; }

describe('HomeHero investor tier', () => {
  it('renders the cooler, emoji-free greeting for an investor', () => {
    render(wrap(<HomeHero />));
    // investor continue copy: "Welcome back, Sam. Pick up where you left off: ..."
    const greeting = screen.getByText(/Welcome back, Sam\./);
    expect(/\p{Extended_Pictographic}/u.test(greeting.textContent ?? '')).toBe(false);
  });

  it('shows the Investor tier chip near the greeting', () => {
    render(wrap(<HomeHero />));
    expect(screen.getByLabelText('Investor mode')).toBeInTheDocument();
  });
});
