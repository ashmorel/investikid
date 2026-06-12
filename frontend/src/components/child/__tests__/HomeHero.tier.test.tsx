/**
 * HomeHero.tier.test.tsx
 * Tests that HomeHero correctly wires tier config:
 *   - explorer: Penny avatar + speech-bubble + playful HeroCard + "Continue learning" eyebrow
 *   - investor: plain heading (no Penny) + flat HeroCard + "Continue" eyebrow
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { axe } from 'vitest-axe';

// continue-mode next lesson fixture
const nextContinue = {
  mode: 'continue' as const,
  moduleId: 'm1', levelId: 'l1', lessonId: 'q1',
  moduleTitle: 'Stocks', moduleIcon: '📈', lessonLabel: 'What is a Stock?',
  to: '/lessons/m1/l1/q1', isLoading: false,
};

// ── Shared static mocks (non-session hooks) ──────────────────────────────────
vi.mock('@/hooks/useNextLesson', () => ({ useNextLesson: () => nextContinue }));
vi.mock('@/hooks/useProgress', () => ({ useProgress: () => ({ data: { streak_count: 0 } }) }));
vi.mock('@/api/ai', () => ({
  useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
  useHomeGreeting: () => ({ data: undefined }),
}));

function wrap(ui: React.ReactNode) {
  return <MemoryRouter>{ui}</MemoryRouter>;
}

// ── Explorer tier ─────────────────────────────────────────────────────────────
describe('HomeHero — explorer tier', () => {
  vi.mock('@/hooks/useChildSession', () => ({
    useChildSession: () => ({ data: { username: 'Sam', is_premium: false, age_tier: 'explorer' } }),
  }));

  // Re-import HomeHero using the explorer mock (static module-level mock wins here)
  let HomeHero: typeof import('../HomeHero').default;

  beforeEach(async () => {
    const mod = await import('../HomeHero');
    HomeHero = mod.default;
  });

  it('renders penny-greeting testid (Penny avatar present)', () => {
    render(wrap(<HomeHero />));
    expect(screen.getByTestId('penny-greeting')).toBeInTheDocument();
  });

  it('HeroCard uses playful variant (bg-brand-gradient present)', () => {
    const { container } = render(wrap(<HomeHero />));
    expect(container.querySelector('.bg-brand-gradient')).not.toBeNull();
  });

  it('HeroCard eyebrow says "Continue learning" in continue mode', () => {
    render(wrap(<HomeHero />));
    // eyebrow is uppercase in the DOM but we match case-insensitively
    expect(screen.getByText(/continue learning/i)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<HomeHero />));
    expect(await axe(container)).toHaveNoViolations();
  });
});

// ── Investor tier ─────────────────────────────────────────────────────────────
// Must use a separate module scope (resetModules) so the investor session
// mock overrides the explorer mock above.
describe('HomeHero — investor tier', () => {
  let HomeHeroInvestor: typeof import('../HomeHero').default;

  beforeEach(async () => {
    vi.resetModules();
    vi.doMock('@/hooks/useChildSession', () => ({
      useChildSession: () => ({ data: { username: 'Sam', is_premium: false, age_tier: 'investor' } }),
    }));
    vi.doMock('@/hooks/useNextLesson', () => ({ useNextLesson: () => nextContinue }));
    vi.doMock('@/hooks/useProgress', () => ({ useProgress: () => ({ data: { streak_count: 0 } }) }));
    vi.doMock('@/api/ai', () => ({
      useRecommendations: () => ({ data: { review_summary: { due_count: 0 } } }),
      useHomeGreeting: () => ({ data: undefined }),
    }));
    const mod = await import('../HomeHero');
    HomeHeroInvestor = mod.default;
  });

  it('no penny-greeting testid (Penny avatar absent)', () => {
    const { queryByTestId } = render(wrap(<HomeHeroInvestor />));
    expect(queryByTestId('penny-greeting')).toBeNull();
  });

  it('#home-hero-greeting element still present for aria-labelledby', () => {
    const { container } = render(wrap(<HomeHeroInvestor />));
    expect(container.querySelector('#home-hero-greeting')).not.toBeNull();
  });

  it('HeroCard uses flat variant (no .bg-brand-gradient in hero area)', () => {
    const { container } = render(wrap(<HomeHeroInvestor />));
    expect(container.querySelector('.bg-brand-gradient')).toBeNull();
  });

  it('HeroCard eyebrow says "Continue" (not "Continue learning")', () => {
    render(wrap(<HomeHeroInvestor />));
    // The eyebrow text is "CONTINUE" (uppercase via CSS, text content is "Continue")
    // We use getAllByText since the CTA button also says "Continue"
    const elements = screen.getAllByText(/^continue$/i);
    // At least one element should be the eyebrow (a <p>) — not a link
    const eyebrow = elements.find(el => el.tagName === 'P');
    expect(eyebrow).toBeDefined();
    // And "Continue learning" should not exist
    expect(screen.queryByText(/continue learning/i)).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(wrap(<HomeHeroInvestor />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
