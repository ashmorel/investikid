# Home Hierarchy Redesign (M3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild child Home around one dominant "Continue" action — greeting → hero → combined stats card → quick-link chips → slim premium row → browse button — with an investor-tier flat skin, per `docs/superpowers/specs/2026-06-12-home-hierarchy-redesign-design.md`.

**Architecture:** Pure frontend recomposition (no backend/API change). New `StatsCard` replaces `StatsBar`+`LevelProgressCard`; new `QuickLinksRow` replaces `PortfolioSnapshotCard`/`ReviewBanner`/`AchievementsStrip`; `PremiumUpsellCard` becomes a slim one-line row (it is Home-only); `HeroCard` gains a `variant` prop driven by three new `tierConfig` knobs. Modules grid leaves Home.

**Tech Stack:** React 18 + TS, Tailwind v4, vitest + @testing-library/react + vitest-axe. Working dir: `/Users/leeashmore/investikid/frontend`, branch `testing`. Run tests with `npx vitest run <path>`.

**Conventions:** Components in `src/components/child/`, tests in sibling `__tests__/`. Emoji always `aria-hidden` with text alternatives. Tap targets ≥44px. Commit per task, messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 1: tierConfig knobs

**Files:**
- Modify: `src/lib/ageTier.ts` (tierConfig type + both tier objects)
- Test: `tests/unit/age-tier-config.test.ts` (create)

- [ ] **Step 1: Write the failing test**

```ts
// tests/unit/age-tier-config.test.ts
import { describe, expect, it } from 'vitest';
import { tierConfig } from '@/lib/ageTier';

describe('tierConfig home-redesign knobs', () => {
  it('explorer is playful with Penny and emoji', () => {
    expect(tierConfig.explorer.heroVariant).toBe('playful');
    expect(tierConfig.explorer.showPennyAvatar).toBe(true);
    expect(tierConfig.explorer.chipEmoji).toBe(true);
  });
  it('investor is flat, no Penny, no emoji', () => {
    expect(tierConfig.investor.heroVariant).toBe('flat');
    expect(tierConfig.investor.showPennyAvatar).toBe(false);
    expect(tierConfig.investor.chipEmoji).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/unit/age-tier-config.test.ts`
Expected: FAIL — `heroVariant` undefined.

- [ ] **Step 3: Write minimal implementation**

In `src/lib/ageTier.ts`, add to the `tierConfig` record type and both entries:

```ts
export type HeroVariant = 'playful' | 'flat';

// inside the Record value type:
    heroVariant: HeroVariant;
    showPennyAvatar: boolean;
    chipEmoji: boolean;

// entries:
  explorer: { pennyHeroSize: 44, density: 'cozy', celebration: 'big', showTierChip: false, heroVariant: 'playful', showPennyAvatar: true, chipEmoji: true },
  investor: { pennyHeroSize: 32, density: 'compact', celebration: 'subtle', showTierChip: true, heroVariant: 'flat', showPennyAvatar: false, chipEmoji: false },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/unit/age-tier-config.test.ts` — Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/lib/ageTier.ts tests/unit/age-tier-config.test.ts
git commit -m "feat(m3): tierConfig knobs heroVariant/showPennyAvatar/chipEmoji

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

### Task 2: HeroCard `variant` prop (flat skin + bigger title)

**Files:**
- Modify: `src/components/child/ui/HeroCard.tsx`
- Test: `src/components/child/ui/__tests__/HeroCard.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/child/ui/__tests__/HeroCard.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { HeroCard } from '../HeroCard';

const renderCard = (variant?: 'playful' | 'flat') =>
  render(
    <MemoryRouter>
      <HeroCard eyebrow="Continue learning" icon="📈" title="What is a Stock?" subtitle="Level 2 · Lesson 3" cta="Continue" to="/lessons/1/2/3" variant={variant} />
    </MemoryRouter>,
  );

describe('HeroCard variants', () => {
  it('defaults to playful (gradient) and shows the icon', () => {
    const { container } = renderCard();
    expect(container.querySelector('.bg-brand-gradient')).not.toBeNull();
    expect(screen.getByText('📈')).toBeInTheDocument();
  });
  it('flat variant is a white bordered card without the emoji icon', () => {
    const { container } = renderCard('flat');
    expect(container.querySelector('.bg-brand-gradient')).toBeNull();
    expect(container.querySelector('.bg-white')).not.toBeNull();
    expect(screen.queryByText('📈')).toBeNull();
  });
  it('has no axe violations in both variants', async () => {
    expect(await axe(renderCard().container)).toHaveNoViolations();
    expect(await axe(renderCard('flat').container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `npx vitest run src/components/child/ui/__tests__/HeroCard.test.tsx` (variant prop unknown / flat assertions fail).

- [ ] **Step 3: Implement**

Replace `src/components/child/ui/HeroCard.tsx` with:

```tsx
import { motion } from 'framer-motion';
import { GradientButton } from './GradientButton';

type Props = {
  eyebrow: string;
  icon?: string;
  title: string;
  subtitle?: string;
  cta: string;
  to: string;
  variant?: 'playful' | 'flat';
};

export function HeroCard({ eyebrow, icon, title, subtitle, cta, to, variant = 'playful' }: Props) {
  const flat = variant === 'flat';
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.35 }}
      className={
        flat
          ? 'overflow-hidden rounded-xl border border-gray-200 bg-white p-5 text-gray-900 shadow-sm'
          : 'overflow-hidden rounded-3xl bg-brand-gradient p-6 text-white shadow-lg shadow-brand-600/30'
      }
    >
      <p className={`text-xs font-extrabold uppercase tracking-wider ${flat ? 'text-gray-400' : 'opacity-95'}`}>
        {!flat && <span aria-hidden="true">▶ </span>}{eyebrow}
      </p>
      <div className="mt-2 flex items-center gap-3">
        {icon && !flat && (
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-2xl" aria-hidden="true">{icon}</span>
        )}
        <p className="text-xl font-extrabold leading-tight">{title}</p>
      </div>
      {subtitle && <p className={`mt-1 text-sm font-medium ${flat ? 'text-gray-500' : 'opacity-90'}`}>{subtitle}</p>}
      <GradientButton
        to={to}
        full
        className={
          flat
            ? 'mt-4 !bg-none bg-brand-700 text-white shadow-none hover:bg-brand-800'
            : 'mt-4 !bg-none bg-white text-brand-700 shadow-none hover:bg-brand-50'
        }
      >
        {cta}<span aria-hidden="true"> →</span>
      </GradientButton>
    </motion.div>
  );
}
```

- [ ] **Step 4: Run to verify PASS**, plus `npx vitest run src/components/child/__tests__` to catch HomeHero regressions (playful remains the default).

- [ ] **Step 5: Commit** — `feat(m3): HeroCard flat variant + larger title`

### Task 3: HomeHero — tier-driven greeting + hero variant

**Files:**
- Modify: `src/components/child/HomeHero.tsx`
- Test: existing HomeHero/greeting tests (run, update if greeting markup assertions break); add cases to `src/components/child/__tests__/HomeHero.tier.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/child/__tests__/HomeHero.tier.test.tsx
// Mock the session/data hooks the same way existing HomeHero tests do (see
// src/components/child/__tests__/ for the established mock pattern), with
// age_tier controllable per test.
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
// ...mocks for useChildSession (age_tier), useProgress, useRecommendations,
// useHomeGreeting, useNextLesson returning a 'continue' lesson...

describe('HomeHero by tier', () => {
  it('explorer shows the Penny avatar bubble', () => {
    renderWithTier('explorer');
    expect(screen.getByTestId('penny-greeting')).toBeInTheDocument();
  });
  it('investor shows a plain greeting heading, no Penny avatar', () => {
    renderWithTier('investor');
    expect(screen.queryByTestId('penny-greeting')).toBeNull();
    expect(screen.getByText(/welcome back|hi /i)).toBeInTheDocument();
  });
});
```

(Write `renderWithTier` against the real mock shapes found in the existing HomeHero test file — keep greeting text assertions loose; greeting copy comes from `buildHeroGreeting`.)

- [ ] **Step 2: Run to verify it fails** (no `penny-greeting` testid yet).

- [ ] **Step 3: Implement** in `HomeHero.tsx`:

```tsx
const cfg = tierConfig[tier];
// greeting block:
{cfg.showPennyAvatar ? (
  <div className="flex items-start gap-3" data-testid="penny-greeting">
    {/* existing avatar + bubble markup unchanged */}
  </div>
) : (
  <div className="flex min-w-0 flex-col items-start gap-1">
    {cfg.showTierChip && <TierChip />}
    <p id="home-hero-greeting" className="text-lg font-extrabold text-gray-900">{greeting}</p>
  </div>
)}
// hero card: pass variant
<HeroCard ... variant={cfg.heroVariant} eyebrow={next.mode === 'continue' ? (cfg.heroVariant === 'flat' ? 'Continue' : 'Continue learning') : 'Start here'} />
// caught_up branch: when cfg.heroVariant === 'flat', swap the gradient celebration
// container classes for the flat white card classes (same copy/CTA).
```

- [ ] **Step 4: Run** the new test + all existing HomeHero/Home tests. Expected: PASS.

- [ ] **Step 5: Commit** — `feat(m3): tier-driven greeting and hero variant in HomeHero`

### Task 4: StatsCard (merges StatsBar + LevelProgressCard)

**Files:**
- Create: `src/components/child/StatsCard.tsx`
- Test: `src/components/child/__tests__/StatsCard.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/child/__tests__/StatsCard.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { StatsCard } from '../StatsCard';

vi.mock('@/lib/ageTier', async (orig) => ({ ...(await orig()), useAgeTier: () => mockTier }));
let mockTier: 'explorer' | 'investor' = 'explorer';

const props = { xp: 1250, level: 4, streakCount: 5, streakFreezes: 1, lastActivityDate: '2026-06-12', today: new Date('2026-06-12T12:00:00') };

describe('StatsCard', () => {
  it('shows level, streak, freezes and XP progress', () => {
    mockTier = 'explorer';
    render(<StatsCard {...props} />);
    expect(screen.getByText(/Level 4/)).toBeInTheDocument();
    expect(screen.getByText(/5-day streak/)).toBeInTheDocument();
    expect(screen.getByLabelText(/streak freeze/)).toBeInTheDocument();
    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '50'); // 1250 % 100
    expect(screen.getByText(/50 XP to Level 5/)).toBeInTheDocument();
  });
  it('investor tier renders without emoji', () => {
    mockTier = 'investor';
    const { container } = render(<StatsCard {...props} />);
    expect(container.textContent).not.toMatch(/[⭐🔥🛡️]/u);
    expect(screen.getByText(/Level 4/)).toBeInTheDocument();
  });
  it('has no axe violations', async () => {
    mockTier = 'explorer';
    const { container } = render(<StatsCard {...props} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify FAIL** (module not found).

- [ ] **Step 3: Implement**

```tsx
// src/components/child/StatsCard.tsx
import { isStreakActive } from '@/lib/streak';
import { tierConfig, useAgeTier } from '@/lib/ageTier';
import { cn } from '@/lib/utils';

type Props = {
  xp: number;
  level: number;
  streakCount: number;
  streakFreezes: number;
  lastActivityDate: string | null;
  today?: Date;
};

const XP_FOR_NEXT = 100;

export function StatsCard({ xp, level, streakCount, streakFreezes, lastActivityDate, today }: Props) {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const active = isStreakActive(lastActivityDate, today ?? new Date());
  const xpInLevel = xp % XP_FOR_NEXT;
  const pct = Math.min(100, Math.round((xpInLevel / XP_FOR_NEXT) * 100));
  const toGo = XP_FOR_NEXT - xpInLevel;
  return (
    <div className="rounded-2xl border border-brand-200 bg-card p-4 shadow-sm" role="group" aria-label="Your progress">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-extrabold text-ink">
          {emoji && <span aria-hidden="true">⭐ </span>}Level {level}
        </span>
        <span className={cn('text-sm font-bold text-gray-700', !active && 'opacity-50')}>
          {emoji && <span aria-hidden="true">🔥 </span>}
          <span aria-label={active ? 'streak active' : 'streak inactive'}>{streakCount}-day streak</span>
          {streakFreezes > 0 && (
            <span aria-label={`, ${streakFreezes} streak freeze${streakFreezes === 1 ? '' : 's'} — saves your streak if you miss a day`}>
              {emoji ? <span aria-hidden="true"> · 🛡️ ×{streakFreezes}</span> : ` · ${streakFreezes} freeze${streakFreezes === 1 ? '' : 's'}`}
            </span>
          )}
        </span>
      </div>
      <div
        className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-brand-100"
        role="progressbar" aria-valuenow={xpInLevel} aria-valuemin={0} aria-valuemax={XP_FOR_NEXT}
        aria-label={`Level ${level} progress`}
      >
        <div className="h-full rounded-full bg-brand-gradient transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1.5 text-right text-[11px] font-semibold text-muted-foreground">
        {xpInLevel} / {XP_FOR_NEXT} XP · {toGo} XP to Level {level + 1}
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify PASS.**
- [ ] **Step 5: Commit** — `feat(m3): StatsCard combining level/XP/streak`

### Task 5: QuickLinksRow

**Files:**
- Create: `src/components/child/home/QuickLinksRow.tsx`
- Test: `src/components/child/home/__tests__/QuickLinksRow.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

```tsx
// src/components/child/home/__tests__/QuickLinksRow.test.tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { QuickLinksRow } from '../QuickLinksRow';

vi.mock('@/lib/ageTier', async (orig) => ({ ...(await orig()), useAgeTier: () => 'explorer' }));

const renderRow = (p = {}) =>
  render(
    <MemoryRouter>
      <QuickLinksRow portfolioValue="1240.50" currencyCode="USD" reviewDue={2} badgesEarned={7} badgesTotal={24} {...p} />
    </MemoryRouter>,
  );

describe('QuickLinksRow', () => {
  it('renders portfolio, review and badges chips with correct links', () => {
    renderRow();
    expect(screen.getByRole('link', { name: /portfolio/i })).toHaveAttribute('href', '/simulator');
    expect(screen.getByRole('link', { name: /2 to review/i })).toHaveAttribute('href', '/progress');
    expect(screen.getByRole('link', { name: /badges/i })).toHaveAttribute('href', '/stats');
    expect(screen.getByText(/\$1,240\.50/)).toBeInTheDocument();
  });
  it('hides chips without data and hides the row when empty', () => {
    const { container } = renderRow({ portfolioValue: null, reviewDue: 0, badgesEarned: null, badgesTotal: null });
    expect(container.querySelector('nav')).toBeNull();
  });
  it('has no axe violations', async () => {
    expect(await axe(renderRow().container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: Implement**

```tsx
// src/components/child/home/QuickLinksRow.tsx
import { Link } from 'react-router-dom';
import { formatCurrency } from '@/lib/currency';
import { tierConfig, useAgeTier } from '@/lib/ageTier';

type Props = {
  portfolioValue: string | number | null;
  currencyCode: string;
  reviewDue: number;
  badgesEarned: number | null;
  badgesTotal: number | null;
};

const chipBase =
  'inline-flex min-h-[44px] items-center gap-1.5 rounded-2xl px-3.5 py-2 text-xs font-bold shadow-sm ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500';

export function QuickLinksRow({ portfolioValue, currencyCode, reviewDue, badgesEarned, badgesTotal }: Props) {
  const tier = useAgeTier();
  const emoji = tierConfig[tier].chipEmoji;
  const chips: Array<{ key: string; to: string; label: string; text: string; className: string; icon: string }> = [];
  if (portfolioValue != null) {
    chips.push({ key: 'portfolio', to: '/simulator', label: 'Portfolio', text: formatCurrency(portfolioValue, currencyCode), className: 'bg-white text-gray-700', icon: '📊' });
  }
  if (reviewDue > 0) {
    chips.push({ key: 'review', to: '/progress', label: `${reviewDue} to review`, text: '', className: 'bg-accent-100 text-accent-700', icon: '🔁' });
  }
  if (badgesEarned != null && badgesTotal != null) {
    chips.push({ key: 'badges', to: '/stats', label: 'Badges', text: `${badgesEarned} of ${badgesTotal}`, className: 'bg-white text-gray-700', icon: '🏅' });
  }
  if (chips.length === 0) return null;
  return (
    <nav aria-label="Shortcuts">
      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500">While you're here</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((c) => (
          <Link key={c.key} to={c.to} className={`${chipBase} ${c.className}`}>
            {emoji && <span aria-hidden="true">{c.icon}</span>}
            <span>{c.label}</span>
            {c.text && <span className="font-extrabold">{c.text}</span>}
          </Link>
        ))}
      </div>
    </nav>
  );
}
```

- [ ] **Step 4: Run to verify PASS.**
- [ ] **Step 5: Commit** — `feat(m3): QuickLinksRow chips for portfolio/review/badges`

### Task 6: PremiumUpsellCard → slim row

**Files:**
- Modify: `src/components/child/PremiumUpsellCard.tsx` (Home-only component — rewrite in place)
- Test: `src/components/child/__tests__/PremiumUpsellCard.test.tsx` (update assertions)

- [ ] **Step 1: Update the test** — keep existing behaviour cases (hidden for premium, dismissible via `premiumNudge`, opens paywall) and change markup expectations to the slim row:

```tsx
it('renders a single-line upsell with paywall CTA', () => {
  render(<PremiumUpsellCard isPremium={false} />);
  expect(screen.getByText(/unlock all levels & the ai coach/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /ask my grown-up/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: Implement** — rewrite the card body (keep `KEY`, dismissal, `usePremiumPaywall`):

```tsx
return (
  <div className="flex min-h-[44px] items-center gap-2 rounded-2xl border border-accent-200 bg-accent-50 px-3.5 py-2">
    <Sparkles className="h-4 w-4 shrink-0 text-accent-700" aria-hidden="true" />
    <p className="min-w-0 flex-1 truncate text-xs font-bold text-gray-800">Unlock all levels & the AI coach</p>
    <button type="button" onClick={() => open({ kind: 'home', label: 'Premium' })}
      className="shrink-0 rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500">
      Ask my grown-up
    </button>
    <button type="button" onClick={() => { dismissNudge(KEY); setHidden(true); }} aria-label="Dismiss"
      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-accent-700 hover:bg-accent-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500">
      <X className="h-4 w-4" aria-hidden="true" />
    </button>
  </div>
);
```

(`PREMIUM_BENEFITS` import goes away; remove the `<h2>`/list. Note: tap-target sanity — the dismiss button is 32px visual inside a ≥44px row, same pattern as the current card.)

- [ ] **Step 4: Run PremiumUpsellCard + premium a11y tests.** Expected: PASS.
- [ ] **Step 5: Commit** — `feat(m3): slim premium upsell row`

### Task 7: Recompose Home + delete replaced components

**Files:**
- Modify: `src/pages/child/Home.tsx`
- Delete: `src/components/child/StatsBar.tsx`, `src/components/child/LevelProgressCard.tsx`, `src/components/child/home/PortfolioSnapshotCard.tsx`, `src/components/child/ReviewBanner.tsx`, `src/components/child/AchievementsStrip.tsx` + their `__tests__` files + `tests/a11y/portfolio-snapshot.a11y.test.tsx`
- Test: `src/pages/child/__tests__/Home.test.tsx` (update)

- [ ] **Step 1: Update Home test first** — assert the new composition:

```tsx
it('renders sections in hierarchy order and no modules grid', () => {
  renderHome();
  const main = screen.getByRole('heading', { name: /your learning home/i });
  expect(main).toBeInTheDocument();
  expect(screen.getByRole('group', { name: /your progress/i })).toBeInTheDocument();   // StatsCard
  expect(screen.getByRole('navigation', { name: /shortcuts/i })).toBeInTheDocument(); // QuickLinksRow
  expect(screen.queryByRole('region', { name: /your modules/i })).toBeNull();
  expect(screen.queryByText(/your modules/i)).toBeNull();
  expect(screen.getByRole('link', { name: /browse all modules/i })).toBeInTheDocument();
});
```

(Adapt to the existing Home.test.tsx mock setup; drop assertions about the removed cards.)

- [ ] **Step 2: Run to verify FAIL.**

- [ ] **Step 3: Implement Home.tsx** — new return block:

```tsx
return (
  <div className="mx-auto max-w-3xl px-4 py-4 sm:px-6 sm:py-6">
    <h1 className="sr-only">Your learning home</h1>
    <HomeHero />
    <div className="mt-4">
      <StatsCard
        xp={xp} level={level}
        streakCount={progress?.streak_count ?? 0}
        streakFreezes={progress?.streak_freezes ?? 0}
        lastActivityDate={progress?.last_activity_date ?? null}
      />
    </div>
    <div className="mt-4">
      <QuickLinksRow
        portfolioValue={portfolio?.total_value ?? null}
        currencyCode={portfolio?.currency_code ?? 'USD'}
        reviewDue={recs?.review_summary.due_count ?? 0}
        badgesEarned={earnedBadges.data?.length ?? null}
        badgesTotal={allBadges.data?.length ?? null}
      />
    </div>
    <div className="mt-4">
      <PremiumUpsellCard isPremium={me?.is_premium ?? false} />
    </div>
    <div className="mt-5">
      <Button asChild className="bg-brand-gradient hover:brightness-110 text-white font-bold rounded-xl">
        <Link to="/lessons">Browse all modules →</Link>
      </Button>
    </div>
  </div>
);
```

Remove now-unused imports (`StatsBar`, `LevelProgressCard`, `PortfolioSnapshotCard`, `ReviewBanner`, `AchievementsStrip`, `ModuleTile`, `orderModulesForTier`, `densityGridGap`, module query/styleFor if Home-only). Check `earnedBadges.data`/`allBadges.data` shapes in the deleted `AchievementsStrip` for the right count expressions before using `.length`.

- [ ] **Step 4: Delete the five components + their tests.** Run `grep -rn "StatsBar\|LevelProgressCard\|PortfolioSnapshotCard\|ReviewBanner\|AchievementsStrip" src tests` — expect zero hits. Run the full Home/child tests.

- [ ] **Step 5: Commit** — `feat(m3): hero-first Home composition; remove modules grid + merged cards`

### Task 8: A11y group + both-tier axe pass

**Files:**
- Modify: `tests/a11y/child-core.a11y.test.tsx` (Home is part of child core)

- [ ] **Step 1:** Update/extend the child-core a11y test so Home renders with the new composition and runs axe for BOTH tiers (mock `useAgeTier`/session age_tier per case). Expected first run: may fail on stale queries for removed components — fix test setup, not the components.

- [ ] **Step 2:** `npx vitest run tests/a11y` — Expected: PASS, zero violations.

- [ ] **Step 3: Commit** — `test(m3): a11y coverage for redesigned Home (both tiers)`

### Task 9: Full verification + push

- [ ] **Step 1:** `npx tsc -b` — clean.
- [ ] **Step 2:** `npm run lint` — zero errors.
- [ ] **Step 3:** `npx vitest run` — full suite green.
- [ ] **Step 4:** `npm run build` — clean. Then `npx cap sync ios` (copy-only; USER Xcode rebuild needed to see on device).
- [ ] **Step 5:** Push `testing`, confirm CI green: `git push origin testing && gh run watch $(gh run list --branch testing --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status`
- [ ] **Step 6:** Update `docs/2026-06-12-market-leader-roadmap.md` — mark M3 build done (pending device QA + analytics instrumentation note for M4). Commit.
