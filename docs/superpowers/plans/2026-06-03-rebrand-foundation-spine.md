# Rebrand Foundation & Spine (SP-A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin InvestiKid from amber to the sky-blue "Yasmin's Choice" identity across the whole app via a semantic colour-token system, and swap the mascot from Eddie the robot to Penny the pig (frontend + backend AI persona) — restyle/rebrand only, no routes/data/IA/behaviour change.

**Architecture:** Add a role-based semantic token vocabulary to `src/index.css` `@theme` (Tailwind v4 CSS-first, from SP-0) and repoint the shadcn tokens at it; then convert literal `amber/orange/green/red/yellow/blue` utility classes to the semantic equivalent by role across the app. Add a `Penny` SVG component (3 moods) replacing `RobotEddie`, and rename Eddie→Penny in components, copy, and backend LLM persona prompts (moderation/gating/schemas unchanged).

**Tech Stack:** React 18 + Vite + TS + Tailwind v4 + shadcn/ui; FastAPI backend (persona prompts only).

**Spec:** `docs/superpowers/specs/2026-06-03-rebrand-foundation-spine-design.md`

**Conventions:** Frontend commands from `invest-ed/frontend`: `npx tsc -b`, `npm run lint` (one pre-existing `src/components/ui/button.tsx` fast-refresh warning is the baseline — 0 errors otherwise), `npm test` (vitest + vitest-axe), `npm run build`. Backend from `invest-ed/backend`: `/Users/leeashmore/Local Repo/.venv/bin/pytest`, `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` (local test Postgres can hang ~90s → environmental; rely on CI). Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend only on green CI (5 jobs: frontend, backend, security, a11y, responsive). iOS rebuild is deferred to programme end — do NOT run per task. **This is restyle/rebrand only: never change a route, query, endpoint, data shape, or behaviour — only colours, the mascot component, and persona/visible copy.**

---

## Authoritative colour-mapping table (used by Tasks 2 & 7)

Apply by **role**, not blindly. When a literal class appears, replace with:

| Old literal | New semantic | Notes |
|---|---|---|
| `amber-50/100/200/300/400/500/600/700/800/900` | `brand-<same step>` | the old primary → blue brand |
| `orange-400` | `brand-400` | |
| `orange-500` | `brand-600` | gradient mid/end |
| `orange-600` | `brand-700` | |
| `orange-50/100/200` | `brand-50/100/200` | |
| `from-amber-400 to-orange-500` (gradient) | `bg-brand-gradient` utility (or `from-brand-grad-from to-brand-grad-to`) | declare gradient once |
| `shadow-orange-500/NN` | `shadow-brand-600/NN` | |
| `green-*` / `emerald-*` / `lime-*` | `success-<nearest step>` | gains/correct |
| `red-*` / `rose-*` | `danger-<nearest step>` | loss/errors |
| `yellow-*` (stars) | `accent-<nearest step>` | warm reward colour (amber) |
| amber used for **streak / level / reward / star / XP** chips | `accent-*` (NOT brand) | keep these warm by design |
| `blue-*` / `indigo-*` in **simulator/charts** (must read distinct from brand) | `info-*` | |
| `blue-*` / `indigo-*` elsewhere (decorative/secondary) | `brand-*` | brand is blue now |

**Accessibility overrides (always win over the table):** text on white/light must be ≥ AA — never `brand-300/brand-400` (or `sky-400`) as text on white; use `brand-600/700/900`, `ink`, or `muted-foreground`. Success text → `success-600/700` (never lime). White text only on `brand-*`/gradient at large/bold sizes. Preserve visible focus rings, radiogroup semantics, `aria-hidden` on decorative graphics, ≥16px touch inputs, no `maximum-scale`, safe-area vars.

---

### Task 1: Semantic token vocabulary + repoint shadcn tokens + gradient utility

**Files:**
- Modify (full rewrite): `invest-ed/frontend/src/index.css`
- Create (temporary, NOT committed): `invest-ed/frontend/tmp-shot.mjs` (reused for before/after across tasks)

- [ ] **Step 1: Capture a BEFORE screenshot (amber baseline)**

Create `invest-ed/frontend/tmp-shot.mjs` with the SP-0 parity script content (the mocked-API capturer). Use this exact file:

```js
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
const BASE = 'http://localhost:5188';
const OUT = process.env.OUTDIR || '/tmp/spa/before';
mkdirSync(OUT, { recursive: true });
const me = { id:'u1', email:'maya@example.com', username:'Maya', dob:'2015-01-01', country_code:'GB', currency_code:'GBP', topic_path:null, is_premium:true, is_admin:false, parent_email:'p@example.com', created_at:'2026-01-01T00:00:00Z', email_verified_at:'2026-01-02T00:00:00Z' };
const progress = { xp:340, level:4, streak_count:5, last_activity_date:'2026-06-03' };
const modules = [
  { id:'m1', topic:'savings', title:'Saving Smarts', country_codes:['GB'], is_premium:false, order_index:0, icon:'🐷', locked:false },
  { id:'m2', topic:'budgeting', title:'Budget Boss', country_codes:['GB'], is_premium:false, order_index:1, icon:'📊', locked:false },
  { id:'m3', topic:'stocks', title:'Stock Market 101', country_codes:['GB'], is_premium:false, order_index:2, icon:'📈', locked:false },
  { id:'m4', topic:'crypto', title:'Crypto Curious', country_codes:['GB'], is_premium:true, order_index:3, icon:'🪙', locked:true },
];
const recs = { continue_learning:[{module_id:'m1',title:'Saving Smarts',reason:'Pick up where you left off',mode:'continue'}], something_new:[{module_id:'m3',title:'Stock Market 101',reason:'Try something new',mode:'start'}], review_summary:{due_count:3} };
const levels = [{ id:'l1', module_id:'m1', title:'Level 1 — Basics', order_index:0, is_premium:false, icon:'⭐', state:'in_progress', locked_reason:null, passed:false, lessons_total:3, lessons_completed:1 }];
const levelLessons = [
  { id:'ls1', type:'card', title:'What is saving?', xp_reward:10, order_index:0, completed:true },
  { id:'ls2', type:'quiz', title:'Saving vs spending', xp_reward:15, order_index:1, completed:false },
  { id:'ls3', type:'scenario', title:'The piggy bank choice', xp_reward:20, order_index:2, completed:false },
];
const quizLesson = { id:'ls2', module_id:'m1', type:'quiz', content_json:{ question:'Which is the smartest way to reach a savings goal?', choices:['Spend it all right now','Set aside a little each week','Wait and hope it appears','Borrow from a friend'], answer_index:1, explanation:'Saving a little regularly really adds up!' }, xp_reward:15, order_index:1, completed:false, locked:false };
const greeting = { greeting:"Hi Maya! Nice 5-day streak — let's keep it going." };
const j = (route, body) => route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify(body) });
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport:{ width:390, height:844 }, deviceScaleFactor:2 });
const page = await ctx.newPage();
await page.route('**/*', (route) => {
  const p = new URL(route.request().url()).pathname;
  if (p === '/users/me') return j(route, me);
  if (p === '/users/me/progress') return j(route, progress);
  if (p === '/users/me/badges') return j(route, []);
  if (p === '/modules') return j(route, modules);
  if (p === '/recommendations') return j(route, recs);
  if (p === '/profile/mastery') return j(route, { topics:[], weak_concepts:[] });
  if (p === '/profile/strengths') return j(route, { strengths:[], gaps:[] });
  if (p === '/home-greeting') return j(route, greeting);
  if (p === '/leaderboard') return j(route, []);
  if (/^\/modules\/m1\/levels$/.test(p)) return j(route, levels);
  if (/^\/levels\/l1\/lessons$/.test(p)) return j(route, levelLessons);
  if (/^\/lessons\/ls2$/.test(p)) return j(route, quizLesson);
  if (/^\/lessons\/.+\/(view|complete|practice)$/.test(p)) return j(route, { ok:true });
  return route.continue();
});
await ctx.addCookies([{ name:'csrf_token', value:'test', domain:'localhost', path:'/' }]);
await page.goto(`${BASE}/home`, { waitUntil:'networkidle' }); await page.waitForTimeout(1200);
await page.screenshot({ path:`${OUT}/01-home.png`, fullPage:true });
await page.goto(`${BASE}/lessons/m1/l1/ls2`, { waitUntil:'networkidle' }); await page.waitForTimeout(900);
await page.screenshot({ path:`${OUT}/02-quiz.png`, fullPage:true });
await browser.close(); console.log('captured to', OUT);
```

Run (from `invest-ed/frontend`):
```bash
(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; \
  for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/spa/before node tmp-shot.mjs ; pkill -f "port 5188"
```
Expected: two PNGs in `/tmp/spa/before` (amber Home + quiz). These are the "before".

- [ ] **Step 2: Rewrite `src/index.css` with the semantic tokens**

Overwrite `invest-ed/frontend/src/index.css` with exactly:

```css
@import "tailwindcss";
@import "tw-animate-css";

/* Preserve class-based dark mode (matches the prior darkMode: ['class']). */
@custom-variant dark (&:is(.dark *));

@theme {
  /* === Brand — sky→blue ramp (replaces amber/orange) === */
  --color-brand-50: #f0f9ff;
  --color-brand-100: #e0f2fe;
  --color-brand-200: #bae6fd;
  --color-brand-300: #7dd3fc;
  --color-brand-400: #38bdf8;
  --color-brand-500: #0ea5e9;
  --color-brand-600: #2563eb;
  --color-brand-700: #1d4ed8;
  --color-brand-800: #1e40af;
  --color-brand-900: #0c4a6e;
  --color-brand-grad-from: #0ea5e9;
  --color-brand-grad-via: #3b82f6;
  --color-brand-grad-to: #4f46e5;

  /* === Accent — demoted amber (streaks, level, rewards, stars) === */
  --color-accent-50: #fffbeb;
  --color-accent-100: #fef3c7;
  --color-accent-200: #fde68a;
  --color-accent-400: #fbbf24;
  --color-accent-500: #f59e0b;
  --color-accent-700: #b45309;

  /* === Success — gains / correct (emerald, AA on white) === */
  --color-success-50: #ecfdf5;
  --color-success-100: #d1fae5;
  --color-success-500: #10b981;
  --color-success-600: #059669;
  --color-success-700: #047857;

  /* === Danger — loss / errors === */
  --color-danger-50: #fef2f2;
  --color-danger-100: #fee2e2;
  --color-danger-500: #ef4444;
  --color-danger-600: #dc2626;
  --color-danger-700: #b91c1c;

  /* === Info — non-brand blue (charts/simulator chrome) === */
  --color-info-100: #e0e7ff;
  --color-info-500: #6366f1;
  --color-info-600: #4f46e5;

  /* === Neutrals / surfaces === */
  --color-surface: #f0f9ff;
  --color-card: #ffffff;
  --color-ink: #0f172a;
  --color-muted: #f1f5f9;
  --color-muted-foreground: #475569;
  --color-line: #bae6fd;

  /* === shadcn semantic tokens repointed to the new palette === */
  --color-background: var(--color-surface);
  --color-foreground: var(--color-ink);
  --color-card-foreground: var(--color-ink);
  --color-popover: #ffffff;
  --color-popover-foreground: var(--color-ink);
  --color-primary: var(--color-brand-500);
  --color-primary-foreground: #ffffff;
  --color-secondary: var(--color-brand-50);
  --color-secondary-foreground: var(--color-brand-900);
  --color-destructive: var(--color-danger-500);
  --color-destructive-foreground: #ffffff;
  --color-accent-foreground: var(--color-brand-900);
  --color-border: var(--color-line);
  --color-input: var(--color-line);
  --color-ring: var(--color-brand-500);

  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
}

/* Brand gradient declared once (hero / primary CTA). */
@utility bg-brand-gradient {
  background-image: linear-gradient(
    to bottom right,
    var(--color-brand-grad-from),
    var(--color-brand-grad-via),
    var(--color-brand-grad-to)
  );
}

@layer base {
  :root {
    --radius: 0.75rem;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --safe-left: env(safe-area-inset-left, 0px);
    --safe-right: env(safe-area-inset-right, 0px);
  }
  * { @apply border-border; }
  html, body, #root {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
  }
  body { @apply bg-background text-foreground; font-family: ui-sans-serif, system-ui, sans-serif; }
  @media (pointer: coarse) {
    input:not([type='checkbox']):not([type='radio']):not([type='range']),
    select,
    textarea {
      font-size: 16px !important;
    }
  }
  :focus-visible { scroll-margin-top: 4.5rem; scroll-margin-bottom: 5rem; }
}
```

Notes for the implementer: `--color-accent` (shadcn bare `accent`, used by some hover states) is intentionally NOT defined as a single token here — `accent-50/100/200/400/500/700` provide the warm amber scale (`bg-accent-100` etc.). Any component using bare `bg-accent`/`text-accent` (rare; shadcn hover) should be changed to `bg-brand-50`/`text-brand-900` during the sweeps. If `npm run build` reports an unknown `accent`/`muted` utility, that means a component used the bare shadcn class — note it for Task 2/7, don't add the token back.

- [ ] **Step 3: Verify build + lint + tests still pass (app still uses literal amber, renders fine)**

Run (from `invest-ed/frontend`):
```bash
npm run build && npx tsc -b && npm run lint && npm test
```
Expected: build OK; tsc clean; lint = only the `button.tsx` warning (plus possible `tmp-shot.mjs` errors — ignore, it's untracked & uncommitted); vitest 503 green. The app still references literal `amber-*` classes which v4 still generates (default palette), so nothing breaks; only the few repointed shadcn tokens (`bg-primary`, `bg-background`, `ring`, `border`) now render blue.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/index.css
git commit -m "feat(rebrand): add semantic colour token vocabulary (sky-blue brand)

Adds brand/accent/success/danger/info/surface scales + bg-brand-gradient
utility to the @theme; repoints shadcn tokens (primary/background/ring/
border/destructive) to the new palette. Literal amber usages recoloured in
later tasks.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
(`tmp-shot.mjs` stays untracked — do NOT add it.)

---

### Task 2: Recolour shared primitives + shell to semantic tokens

Re-skins Home + the lesson flow (they consume these). Apply the mapping table + a11y overrides.

**Files (modify):**
- `invest-ed/frontend/src/components/child/ui/GradientButton.tsx`
- `invest-ed/frontend/src/components/child/ui/HeroCard.tsx`
- `invest-ed/frontend/src/components/child/ui/StatChip.tsx`
- `invest-ed/frontend/src/components/child/ui/ModuleTile.tsx`
- `invest-ed/frontend/src/components/child/ui/OptionCard.tsx`
- `invest-ed/frontend/src/components/child/ui/FeedbackPanel.tsx`
- `invest-ed/frontend/src/components/child/lesson/LessonChrome.tsx`
- `invest-ed/frontend/src/components/child/Shell.tsx`
- `invest-ed/frontend/src/components/child/TopNav.tsx`
- `invest-ed/frontend/src/components/child/BottomTabBar.tsx`
- `invest-ed/frontend/src/pages/child/Home.tsx` (the `TOPIC_STYLE` hex map + gradient button)
- Tests under the matching `__tests__` dirs (only if they assert a colour class string)

- [ ] **Step 1: Apply the mapping table to each file**

For every file above, replace literal `amber-*`/`orange-*`/`green-*`/`red-*`/`yellow-*` utility classes per the mapping table. Specifics:
- **GradientButton:** the `from-amber-400 to-orange-500 hover:from-amber-500 hover:to-orange-600` becomes `bg-brand-gradient` plus a `hover:brightness-110` (gradients can't be hover-shaded per-stop cleanly); keep the white extrabold label, focus ring (`focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2`).
- **HeroCard / Home hero:** `from-amber-400 to-orange-500` → `bg-brand-gradient`; the white-pill CTA keeps `text-brand-700` (was amber-700).
- **StatChip:** XP/level/streak are **rewards** → use `accent-*` (amber) for the warm chips (e.g. `bg-accent-100 text-accent-700`), EXCEPT a generic/brand chip → `bg-brand-50 text-brand-700`.
- **ModuleTile:** the default `{ accent:'#fbbf24', tint:'#fff4d6' }` fallback and the "recommended" marker → use brand-tinted defaults (`accent:'#0ea5e9', tint:'#e0f2fe'`); keep per-topic colours but from the new family.
- **Home `TOPIC_STYLE`:** re-pitch each topic's `{accent,tint}` hex into the new family (e.g. savings `#0ea5e9/#e0f2fe`, budgeting `#10b981/#d1fae5`, stocks `#6366f1/#e0e7ff`, risk `#8b5cf6/#ede9fe`, crypto `#4f46e5/#e0e7ff`, taxes `#f43f5e/#ffe4e6`, debt `#14b8a6/#d7f5f1`, entrepreneurship `#f59e0b/#fef3c7`, real_estate `#eab308/#fef9c3`). Keep the map shape unchanged.
- **OptionCard:** selected = `border-brand-500 bg-brand-50`; correct = `border-success-500 bg-success-50`; incorrect = `border-danger-500 bg-danger-50`; letter badge selected `bg-brand-500 text-white`.
- **FeedbackPanel:** Correct = `success-*`; Not-quite = `danger-*` (coral→rose ok) — ensure text uses `success-700`/`danger-700` for AA.
- **LessonChrome:** progress bar fill `bg-brand-gradient` or `bg-brand-500`; XP badge → `accent-*`; the speech-bubble border `border-brand-200`.
- **Shell:** the `from-amber-50 to-orange-50` page background → `bg-surface` (or `from-brand-50 to-brand-50`); loading header border `border-brand-200`.
- **TopNav / BottomTabBar:** active = `text-brand-600` + `bg-brand-100` chip; the header coin/logo gradient → `bg-brand-gradient`. (Tab labels/icons & routes unchanged.)

Apply the a11y overrides: any text on white that resolves to `brand-300/400` must be bumped to `brand-600/700`.

- [ ] **Step 2: Update any colour-asserting tests**

Run `grep -rl "amber-\|orange-" invest-ed/frontend/src/components/child/**/__tests__ invest-ed/frontend/src/pages/child/__tests__ 2>/dev/null`. For each test that asserts an old colour class, update the expected string to the new semantic class. Do NOT weaken behavioural assertions.

- [ ] **Step 3: Verify**

Run (from `invest-ed/frontend`):
```bash
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: tsc clean; lint = button.tsx warning only (ignore tmp-shot.mjs); vitest green; build OK.

- [ ] **Step 4: Visual check (AFTER for the spine)**

Run the capture (from `invest-ed/frontend`):
```bash
(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; \
  for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/spa/after-t2 node tmp-shot.mjs ; pkill -f "port 5188"
```
Read `/tmp/spa/after-t2/01-home.png` + `02-quiz.png`: Home + lesson should now be **blue** (hero gradient, tabs, progress) with warm amber **only** on streak/XP/level chips. Confirm no leftover amber on primary surfaces. (RobotEddie is still the robot here — that changes in Task 4.)

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child invest-ed/frontend/src/pages/child/Home.tsx
git commit -m "feat(rebrand): recolour shared primitives + shell to semantic tokens

GradientButton/HeroCard/StatChip/ModuleTile/OptionCard/FeedbackPanel/
LessonChrome + Shell/TopNav/BottomTabBar + Home topic palette now use the
sky-blue brand tokens (warm accent kept for streak/XP/level). Re-skins
Home and the lesson flow.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Penny mascot component (3 moods) + tests

**Files:**
- Create: `invest-ed/frontend/src/components/child/ui/Penny.tsx`
- Create: `invest-ed/frontend/src/components/child/ui/__tests__/Penny.test.tsx`

- [ ] **Step 1: Write the component**

Create `invest-ed/frontend/src/components/child/ui/Penny.tsx` (ported from the prototype's `MascotTip` pig avatar — just the mascot, no speech bubble; mood-driven gradient; `useId` for unique ids; `aria-hidden`):

```tsx
import { useId } from 'react';

type Mood = 'happy' | 'thinking' | 'excited';

const MOOD_GRADIENT: Record<Mood, [string, string]> = {
  happy: ['#38bdf8', '#2563eb'],     // sky-400 → blue-600
  thinking: ['#818cf8', '#4f46e5'],  // indigo-400 → indigo-600
  excited: ['#f59e0b', '#f43f5e'],   // amber-500 → rose-500
};

export function Penny({
  size = 48,
  mood = 'happy',
  className,
}: {
  size?: number;
  mood?: Mood;
  className?: string;
}) {
  const uid = useId();
  const gradId = `penny-${uid}`;
  const [from, to] = MOOD_GRADIENT[mood];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop stopColor={from} />
          <stop offset="1" stopColor={to} />
        </linearGradient>
      </defs>
      {/* Head */}
      <circle cx="28" cy="28" r="26" fill={`url(#${gradId})`} />
      <circle cx="28" cy="28" r="22" fill="white" fillOpacity="0.18" />
      {/* Ears */}
      <ellipse cx="10" cy="22" rx="5" ry="7" fill="white" fillOpacity="0.4" />
      <ellipse cx="46" cy="22" rx="5" ry="7" fill="white" fillOpacity="0.4" />
      {/* Eyes */}
      {mood === 'excited' ? (
        <>
          <text x="16" y="31" fontSize="11" fill="white">★</text>
          <text x="33" y="31" fontSize="11" fill="white">★</text>
        </>
      ) : (
        <>
          <ellipse cx="21" cy="26" rx="3.5" ry="3" fill="white" />
          <ellipse cx="35" cy="26" rx="3.5" ry="3" fill="white" />
          <circle cx={mood === 'thinking' ? 22 : 21.5} cy="26" r="2" fill="#0c4a6e" />
          <circle cx={mood === 'thinking' ? 36 : 35.5} cy="26" r="2" fill="#0c4a6e" />
        </>
      )}
      {/* Snout */}
      <ellipse cx="28" cy="35" rx="6" ry="4" fill="white" fillOpacity="0.35" />
      <circle cx="26" cy="35" r="1" fill="white" fillOpacity="0.7" />
      <circle cx="30" cy="35" r="1" fill="white" fillOpacity="0.7" />
      {/* Mouth */}
      <path
        d={mood === 'excited' ? 'M22 39 Q28 44 34 39' : 'M23 38 Q28 42 33 38'}
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
```

- [ ] **Step 2: Write the tests**

Create `invest-ed/frontend/src/components/child/ui/__tests__/Penny.test.tsx`:

```tsx
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { describe, it, expect } from 'vitest';
import { Penny } from '../Penny';

describe('Penny', () => {
  it('renders a decorative svg sized by the size prop', () => {
    const { container } = render(<Penny size={64} />);
    const svg = container.querySelector('svg')!;
    expect(svg).toBeTruthy();
    expect(svg.getAttribute('width')).toBe('64');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
  });

  it('gives each instance a unique gradient id', () => {
    const { container } = render(
      <>
        <Penny />
        <Penny />
      </>,
    );
    const ids = Array.from(container.querySelectorAll('linearGradient')).map((g) => g.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('renders star eyes only in the excited mood', () => {
    const { container: happy } = render(<Penny mood="happy" />);
    const { container: excited } = render(<Penny mood="excited" />);
    expect(happy.querySelectorAll('text').length).toBe(0);
    expect(excited.querySelectorAll('text').length).toBe(2);
  });

  it('has no axe violations', async () => {
    const { container } = render(<Penny />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 3: Run the tests**

Run (from `invest-ed/frontend`):
```bash
npm test -- src/components/child/ui/__tests__/Penny.test.tsx
```
Expected: 4 tests pass.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/child/ui/Penny.tsx invest-ed/frontend/src/components/child/ui/__tests__/Penny.test.tsx
git commit -m "feat(rebrand): add Penny pig mascot component (happy/thinking/excited)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Move mascot callers to Penny + retire RobotEddie + rename EddieFAB→PennyFAB

**Files:**
- Modify: `invest-ed/frontend/src/components/child/HomeHero.tsx`, `invest-ed/frontend/src/components/child/lesson/LessonChrome.tsx`
- Create: `invest-ed/frontend/src/components/child/PennyFAB.tsx` (renamed from EddieFAB)
- Delete: `invest-ed/frontend/src/components/child/EddieFAB.tsx`, `invest-ed/frontend/src/components/child/ui/RobotEddie.tsx`, `invest-ed/frontend/src/components/child/ui/__tests__/RobotEddie.test.tsx`
- Modify: `invest-ed/frontend/src/components/child/Shell.tsx` (import + usage)
- Rename test: `invest-ed/frontend/src/components/child/__tests__/EddieFAB.test.tsx` → `PennyFAB.test.tsx`

- [ ] **Step 1: Create `PennyFAB.tsx`**

Create `invest-ed/frontend/src/components/child/PennyFAB.tsx`:

```tsx
import { useNavigate } from 'react-router-dom';
import { Penny } from '@/components/child/ui/Penny';

type Props = {
  dueCount: number;
};

export function PennyFAB({ dueCount }: Props) {
  const navigate = useNavigate();

  return (
    <button
      onClick={() => navigate('/coach')}
      aria-label="Open Coach Penny"
      className="fixed bottom-20 right-4 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-brand-gradient shadow-lg transition-transform hover:scale-105 active:scale-95"
    >
      <Penny size={34} mood="happy" />
      {dueCount > 0 && (
        <span
          data-testid="penny-badge"
          className="absolute -right-0.5 -top-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-danger-500"
        />
      )}
    </button>
  );
}
```

- [ ] **Step 2: Delete EddieFAB and RobotEddie (+ its test)**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
git rm src/components/child/EddieFAB.tsx src/components/child/ui/RobotEddie.tsx src/components/child/ui/__tests__/RobotEddie.test.tsx
```

- [ ] **Step 3: Update HomeHero, LessonChrome, Shell**

- `HomeHero.tsx`: replace `import { RobotEddie } ...` with `import { Penny } from '@/components/child/ui/Penny';` and `<RobotEddie size={44} />` with `<Penny size={44} mood="happy" />`.
- `LessonChrome.tsx`: replace the `RobotEddie` import and `<RobotEddie size={40} />` with `<Penny size={40} mood="thinking" />`; update the two `Eddie` code comments to `Penny`.
- `Shell.tsx`: change `import { EddieFAB } from './EddieFAB';` → `import { PennyFAB } from './PennyFAB';` and `<EddieFAB dueCount={...} />` → `<PennyFAB dueCount={...} />`.

- [ ] **Step 4: Rename the FAB test and update it**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
git mv src/components/child/__tests__/EddieFAB.test.tsx src/components/child/__tests__/PennyFAB.test.tsx
```
In `PennyFAB.test.tsx`: update import to `PennyFAB`, the component usage, `aria-label` query `/Open Coach Penny/`, and `data-testid` `penny-badge`.

- [ ] **Step 5: Verify**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: green (button.tsx warning only). No remaining import of RobotEddie/EddieFAB — confirm with `grep -rn "RobotEddie\|EddieFAB" src` → no matches.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add -A invest-ed/frontend/src/components/child
git commit -m "feat(rebrand): replace RobotEddie with Penny; EddieFAB -> PennyFAB

HomeHero/LessonChrome/Shell now render Penny; RobotEddie retired.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Eddie → Penny copy + remaining component renames (frontend)

**Files (modify unless noted):**
- Rename: `invest-ed/frontend/src/components/child/lesson/CoachEddiePanel.tsx` → `CoachPennyPanel.tsx` (+ its test `__tests__/CoachEddiePanel.test.tsx` → `CoachPennyPanel.test.tsx`)
- `invest-ed/frontend/src/components/child/lesson/QuizLesson.tsx`, `ScenarioLesson.tsx` (prop `onShowEddie`→`onShowPenny`, copy "Ask Coach Eddie"→"Ask Coach Penny", `text-amber-600`→`text-brand-700`)
- `invest-ed/frontend/src/pages/child/Lesson.tsx` (`showEddie`→`showPenny`, `setShowEddie`→`setShowPenny`, `onShowEddie`→`onShowPenny`, import `CoachPennyPanel`)
- `invest-ed/frontend/src/pages/child/Coach.tsx` ("Coach Eddie"→"Coach Penny", "Ask Coach Eddie…"→"Ask Coach Penny…")
- `invest-ed/frontend/src/components/child/simulator/ChartGuide.tsx` (`onAskEddie`→`onAskPenny`, "Ask Coach Eddie about this chart"→"Ask Coach Penny about this chart")
- `invest-ed/frontend/src/components/child/simulator/ChartCoachPanel.tsx` ("Coach Eddie"→"Coach Penny")
- `invest-ed/frontend/src/pages/child/Stock.tsx` (`showCoachEddie`→`showCoachPenny`, `setShowCoachEddie`→`setShowCoachPenny`, `onAskEddie`→`onAskPenny`)
- `invest-ed/frontend/src/api/ai.ts` (comment `// --- Coach Eddie ---` → `// --- Coach Penny ---`)
- Tests: `lesson/__tests__/QuizLesson.test.tsx`, `lesson/__tests__/ScenarioLesson.test.tsx`, `__tests__/CoachEddiePanel.test.tsx` (renamed) — update copy/identifier expectations.

- [ ] **Step 1: Rename the Coach panel component + test**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
git mv src/components/child/lesson/CoachEddiePanel.tsx src/components/child/lesson/CoachPennyPanel.tsx
git mv src/components/child/__tests__/CoachEddiePanel.test.tsx src/components/child/__tests__/CoachPennyPanel.test.tsx
```
In `CoachPennyPanel.tsx`: rename the exported function `CoachEddiePanel`→`CoachPennyPanel`; change visible copy "Coach Eddie"→"Coach Penny", "Coach Eddie couldn't answer…"→"Coach Penny couldn't answer…", placeholder "Ask Coach Eddie..."→"Ask Coach Penny...".

- [ ] **Step 2: Apply the renames + copy across the remaining files**

Do the identifier and copy changes listed in **Files** above for each file. These are mechanical rename/copy edits — keep behaviour, props wiring, and handlers identical (only their names/strings change). Also apply the colour mapping (`text-amber-600`→`text-brand-700`, `hover:text-amber-700`→`hover:text-brand-800`) on the "Ask Coach Penny" buttons in QuizLesson/ScenarioLesson.

- [ ] **Step 3: Update the affected tests**

In `QuizLesson.test.tsx`, `ScenarioLesson.test.tsx`, and the renamed `CoachPennyPanel.test.tsx`: update any "Eddie" copy/role queries and imported identifiers to "Penny". Run `grep -rn "Eddie" src` and confirm **zero** matches remain anywhere in `src` (component names, props, copy, comments, tests).

- [ ] **Step 4: Verify**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
npx tsc -b && npm run lint && npm test && npm run build
grep -rn "Eddie" src && echo "FOUND EDDIE (should be empty)" || echo "no Eddie remaining ✓"
```
Expected: green; the grep prints "no Eddie remaining ✓".

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add -A invest-ed/frontend/src
git commit -m "feat(rebrand): rename Eddie -> Penny across frontend copy & components

CoachEddiePanel -> CoachPennyPanel; onShowEddie/onAskEddie -> *Penny;
all visible 'Coach Eddie' copy -> 'Coach Penny'. No Eddie references remain.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Eddie → Penny backend AI persona

Persona copy only — `moderate_output`, `is_premium` gating, rate limits, schemas, endpoints all unchanged.

**Files (modify):**
- `invest-ed/backend/app/core/config.py` (line 57 comment `# Coach Eddie tutor` → `# Coach Penny tutor`)
- `invest-ed/backend/app/services/tutor_service.py` (lines 28, 87)
- `invest-ed/backend/app/services/coach_service.py` (lines 1, 123, 161)
- `invest-ed/backend/app/services/chart_coach_service.py` (line 44)
- `invest-ed/backend/app/services/home_greeting_service.py` (line 16)
- `invest-ed/backend/app/services/alerting.py` (lines 51, 60)

- [ ] **Step 1: Rewrite the persona strings**

Replace each "Coach Eddie" persona reference with "Coach Penny", keeping the surrounding prompt structure. Exact replacements:
- `tutor_service.py:28`: `"You are Coach Eddie, a friendly and encouraging money tutor for kids learning "` → `"You are Coach Penny, a friendly and encouraging piggy-bank money tutor for kids learning "`
- `tutor_service.py:87` docstring: `"""Process a Coach Eddie message and return the response."""` → `"""Process a Coach Penny message and return the response."""`
- `coach_service.py:1` module docstring: `"""Coach Eddie standalone service — context building and action parsing."""` → `"""Coach Penny standalone service — context building and action parsing."""`
- `coach_service.py:123`: `"You are Coach Eddie, a friendly money tutor for kids. You help them navigate "` → `"You are Coach Penny, a friendly piggy-bank money tutor for kids. You help them navigate "`
- `coach_service.py:161` docstring: `"""Process a standalone Coach Eddie message."""` → `"""Process a standalone Coach Penny message."""`
- `chart_coach_service.py:44`: `f"You are Coach Eddie, a friendly investing teacher for a {age}-year-old. "` → `f"You are Coach Penny, a friendly piggy-bank investing teacher for a {age}-year-old. "`
- `home_greeting_service.py:16`: `"You are Coach Eddie, a warm, encouraging money-skills buddy for a child. "` → `"You are Coach Penny, a warm, encouraging piggy-bank money-skills buddy for a child. "`
- `alerting.py:51`: `"A premium AI provider is failing; Coach Eddie is using the fallback provider. "` → `"A premium AI provider is failing; Coach Penny is using the fallback provider. "`
- `alerting.py:60`: `f"All AI providers are unavailable — Coach Eddie is down (path: {path})."` → `f"All AI providers are unavailable — Coach Penny is down (path: {path})."`
- `config.py:57`: `# Coach Eddie tutor` → `# Coach Penny tutor`

- [ ] **Step 2: Confirm no backend test asserts "Eddie"**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed"
grep -rn "Eddie" backend/ && echo "FOUND (update these)" || echo "no Eddie remaining ✓"
```
Expected: "no Eddie remaining ✓" (baseline grep already showed no backend test references; if any appear, update the expected string to "Penny").

- [ ] **Step 3: Lint + targeted tests**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/backend"
/Users/leeashmore/Local Repo/.venv/bin/ruff check .
/Users/leeashmore/Local Repo/.venv/bin/pytest tests/ -k "coach or tutor or chart or greeting or alert" -q
```
Expected: ruff clean; the targeted AI/persona tests pass (they assert structure/moderation, not the name). If the local Postgres hangs the run ~90s, that's environmental — rely on CI (note it and proceed).

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/backend/app
git commit -m "feat(rebrand): rename AI persona Coach Eddie -> Coach Penny (backend)

Persona copy only in tutor/coach/chart_coach/home_greeting/alerting/config.
moderate_output, premium gating, rate limits, and schemas unchanged.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Sweep remaining feature-screen colours to semantic tokens

Everything not already recoloured: simulator, stats, progress, parent, admin, auth, coach, shared non-child components.

**Files:** all remaining files under `invest-ed/frontend/src` that still use literal `amber-*`/`orange-*`/`green-*`/`emerald-*`/`lime-*`/`red-*`/`rose-*`/`yellow-*` and brand-intent `blue-*`/`indigo-*`. Find them:
```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rlE "\b(bg|text|border|from|via|to|ring|fill|stroke|shadow)-(amber|orange|yellow|green|emerald|lime|red|rose)-[0-9]" src
```

- [ ] **Step 1: Apply the mapping table to each remaining file**

For each file, apply the **Authoritative colour-mapping table** + a11y overrides. Role guidance for the feature areas:
- **Simulator (`simulator/*`, `pages/child/Stock.tsx`, `Market.tsx`, `Simulator.tsx`):** gains `text-green-*`→`text-success-600`, losses `text-red-*`→`text-danger-600`; chart/secondary blue → `info-*`; brand chrome (headers, primary buttons) → `brand-*`.
- **Stats / Progress / StrengthsGaps:** brand accents → `brand-*`; positive/mastery → `success-*`; gaps/warnings → `accent-*` or `danger-*` by meaning.
- **Parent / Admin:** primary actions → `brand-*`; destructive → `danger-*`; success toasts → `success-*`. (Admin is lower-traffic; same rules.)
- **Auth (`pages/Login`, `Signup`, etc.):** primary CTA → `bg-brand-gradient`/`bg-primary`; links → `text-brand-700`; errors → `danger-*`.
- **Coach page:** brand chrome → `brand-*` (copy already Penny from Task 5).

- [ ] **Step 2: Update colour-asserting tests**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rlE "amber-|orange-" src --include=*.test.tsx
```
Update any remaining test that asserts an old brand colour class.

- [ ] **Step 3: Verify the sweep is complete**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rnE "\b(bg|text|border|from|via|to|ring|fill|stroke|shadow)-(amber|orange)-[0-9]" src && echo "AMBER REMAINS (fix)" || echo "no amber/orange remaining ✓"
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: "no amber/orange remaining ✓" (green-as-success and red-as-danger literals may legitimately remain only if a non-brand decorative use exists — but prefer semantic tokens); green checks.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add -A invest-ed/frontend/src
git commit -m "feat(rebrand): sweep feature-screen colours to semantic tokens

Simulator, stats, progress, parent, admin, auth, coach now use brand/
success/danger/accent/info tokens. App is fully sky-blue.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Accessibility pass, full regression, before/after, push

**Files:** any touched for a11y fixes (contrast); `tmp-shot.mjs` removed at the end.

- [ ] **Step 1: Contrast audit of text-on-light**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
grep -rnE "text-(brand|info)-(300|400)" src
```
For each hit, decide: if it is **text on a light/white background**, bump to `-600`/`-700` (AA). If it's a label on a dark/gradient surface, it's fine — leave it. Apply fixes.

- [ ] **Step 2: Capture AFTER (full) screenshots and eyeball**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
(npm run dev -- --port 5188 --strictPort >/tmp/dev.log 2>&1 &) ; \
  for i in $(seq 1 40); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/spa/after-final node tmp-shot.mjs ; pkill -f "port 5188"
```
Read `/tmp/spa/after-final/01-home.png` + `02-quiz.png` and compare against `/tmp/spa/before/*`: expect a cohesive **blue + Penny** look (deliberate change, NOT parity), warm amber only on streak/XP/level, readable text everywhere, Penny (not the robot) in the hero + lesson chrome.

- [ ] **Step 3: Full regression (frontend + backend)**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend"
npx tsc -b && npm run lint && npm test && npm run build
cd "/Users/leeashmore/Local Repo/invest-ed/backend"
/Users/leeashmore/Local Repo/.venv/bin/ruff check .
/Users/leeashmore/Local Repo/.venv/bin/pytest -q
```
Expected: frontend green (button.tsx warning only); backend ruff clean + pytest green. If the backend DB-backed run hangs locally (~90s+), that's environmental — rely on CI.

- [ ] **Step 4: Remove temp script, push**

```bash
cd "/Users/leeashmore/Local Repo/invest-ed/frontend" && rm -f tmp-shot.mjs
cd "/Users/leeashmore/Local Repo"
git status --porcelain   # confirm only intended files; tmp-shot.mjs gone
git push origin main
```

- [ ] **Step 5: Confirm green CI**

Watch the run for `main`: all 5 jobs (frontend, backend, security, a11y, responsive) must be green — the **a11y** job (jsx-a11y + vitest-axe + playwright-axe chromium+webkit) is the contrast/role guard. Fix any failure before declaring SP-A done.

- [ ] **Step 6: Report SP-A complete**

Confirm: app fully sky-blue, Penny mascot live (FE + BE persona), semantic tokens in place, CI green. Note the iOS Xcode rebuild remains deferred to programme end. Next: SP-B (child core screen layouts).

---

## Self-Review

**1. Spec coverage:**
- Semantic token vocabulary + repoint + gradient utility → Task 1. ✓
- Recolour primitives + shell → Task 2. ✓
- Penny component (3 moods, useId, aria-hidden) + retire RobotEddie → Tasks 3, 4. ✓
- Eddie→Penny FE rename + copy (19 files + tests) → Tasks 4, 5. ✓
- Eddie→Penny BE persona (6 files) keeping moderation/gating/schemas → Task 6. ✓
- Whole-app colour sweep → Tasks 2 + 7. ✓
- A11y (contrast, focus, radiogroup, ≥16px, safe-area, Penny axe) → Tasks 3, 8 + a11y overrides throughout. ✓
- Testing (unit/axe, backend persona, before/after screenshots, 5 CI jobs) → Tasks 1,3,8. ✓
- Out of scope (layout redesign, routes/data/IA, deps) honoured — colour/mascot/persona only. ✓

**2. Placeholder scan:** No TBD/TODO. Mechanical tasks (2, 5, 7) reference the authoritative mapping table + exact file lists + per-area role guidance + a grep gate, not vague "recolour appropriately." Code-heavy tasks (1, 3, 4, 6) carry full code/exact strings.

**3. Consistency:** Token names (`brand-*`, `accent-*`, `success-*`, `danger-*`, `info-*`, `surface`, `ink`, `line`, `bg-brand-gradient`) are identical across Tasks 1, 2, 7, 8. Component renames consistent: `EddieFAB`→`PennyFAB` (Task 4), `CoachEddiePanel`→`CoachPennyPanel` (Task 5), `Penny` API `{size, mood?, className?}` used the same in Tasks 3/4. Handler renames `onShowEddie`→`onShowPenny`, `onAskEddie`→`onAskPenny`, `showCoachEddie`→`showCoachPenny` consistent between the renaming task (5) and their definitions. The `grep -rn "Eddie" src` gate in Task 5 + `backend/` gate in Task 6 enforce completeness.
