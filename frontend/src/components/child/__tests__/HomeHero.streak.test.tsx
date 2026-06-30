/**
 * HomeHero.streak.test.tsx
 * Covers the B1 daily-progress strip that lives in the hero:
 *   - the streak pill shows when streak_count > 0
 *   - the next-freeze countdown appears when the streak is active and
 *     next_freeze_in > 0 (migrated B6 "freeze visibility" coverage, formerly
 *     on StatsCard which B1 removes from Home).
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/api/cosmetics', () => ({
  useEquippedCosmetics: () => ({ accessories: [], skin: null, background: null }),
}));
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';
import HomeHero from '../HomeHero';

const next = {
  mode: 'continue' as const, moduleId: 'm1', levelId: 'l1', lessonId: 'q1',
  moduleTitle: 'Stocks', moduleIcon: '📈', lessonLabel: 'What is a Stock?',
  to: '/lessons/m1/l1/q1', isLoading: false,
};

vi.mock('@/hooks/useNextLesson', () => ({ useNextLesson: () => next }));
vi.mock('@/hooks/useChildSession', () => ({ useChildSession: () => ({ data: { username: 'Sam', is_premium: false, age_tier: 'explorer' } }) }));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
  useHomeGreeting: () => ({ data: undefined }),
}));

// Active streak: last activity is "today" so isStreakActive() is true regardless
// of when the test runs, and a freeze is on the way in 2 days.
const todayIso = new Date().toISOString().slice(0, 10);
vi.mock('@/hooks/useProgress', () => ({
  useProgress: () => ({
    data: {
      streak_count: 5,
      xp_today: 20,
      daily_goal_xp: 30,
      last_activity_date: todayIso,
      next_freeze_in: 2,
    },
  }),
}));

function wrap(ui: React.ReactNode) { return <MemoryRouter>{ui}</MemoryRouter>; }

describe('HomeHero — daily-progress strip (B1)', () => {
  it('shows the streak pill when streak_count > 0', () => {
    render(wrap(<HomeHero />));
    // The pill is a compact element whose text is exactly the streak label
    // (distinct from the greeting, which embeds the same phrase in a sentence).
    const pill = screen.getByText((_content, el) => el?.textContent === '🔥5-day streak');
    expect(pill).toBeInTheDocument();
  });

  it('shows the next-freeze countdown when streak is active and next_freeze_in > 0', () => {
    render(wrap(<HomeHero />));
    // Migrated B6 freeze-visibility coverage.
    expect(screen.getByText(/next freeze in 2 days/i)).toBeInTheDocument();
  });

  it('shows the daily-goal text', () => {
    render(wrap(<HomeHero />));
    expect(screen.getByText(/today: 20 \/ 30 xp/i)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<HomeHero />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
