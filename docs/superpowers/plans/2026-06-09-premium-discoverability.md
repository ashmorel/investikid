# Premium Discoverability (#4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface Premium proactively via four gentle, dismissible, frequency-capped surfaces (child Home card, earned-moment nudge, parent value/CTA, locked-cue badges), reusing the existing paywall request flow.

**Architecture:** New surfaces are thin entry points that **open the existing global `PremiumPaywall`** (`usePremiumPaywall().open({kind,label})`) — no reimplementation of the request/sent/declined logic. A tiny `localStorage` `premiumNudge` helper handles dismiss + frequency cap. Frontend-only; no backend, no migration.

**Tech Stack:** React 18 + TS + Tailwind v4 + TanStack Query; vitest + vitest-axe.

**Conventions:** TDD. Explicit `git add <paths>` only — never `git add -A`; leave the unrelated `.gitignore` + iOS files alone. Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Verify (from `frontend/`): `npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync`. Work on `testing`; do NOT promote.

**Verified facts:**
- `usePremiumPaywall()` exposes `open(context: {kind: PremiumRequestKind, label: string})`; the global `<PremiumPaywall/>` sheet runs the whole `requestUnlock` → `status ∈ {sent,no_parent,declined,already_sent}` flow with kid-safe copy. Used already: `Module.tsx` calls `openPaywall({kind:'level', label: level.title})`; `LevelCard` premium-locked taps call `onLockedClick` → paywall.
- `frontend/src/api/premium.ts`: `PremiumRequestKind = 'module'|'level'|'challenge'|'ticker'|'coach'`. Backend stores `context_kind` as a free string (≤20) — `'home'` is valid server-side; only the FE union needs widening. `requestUnlock` is per-day deduped (returns `already_sent`).
- `frontend/src/lib/premiumConfig.ts`: `PREMIUM_BENEFITS` (4 strings), `PAYWALL_TITLE`, `PAYWALL_CTA`, `PAYWALL_REQUEST_DECLINED`.
- `PremiumBadge` (`components/child/PremiumBadge.tsx`): `({className?})` → `✨ Premium` (accent tokens).
- `Home.tsx` (child): renders HomeHero, StatsBar, LevelProgressCard, PortfolioSnapshotCard, ReviewBanner, AchievementsStrip, module tiles. Uses `usePremiumPaywall`. Determine `is_premium` from the same source the app already uses client-side (the `['me']` query / premium context that 4B wired for gating — confirm and reuse; do NOT invent a new source).
- `Module.tsx` (post-#1): level cards + a "Module complete → Next module" CTA when all levels complete (`allComplete`). `LevelOut` has `state`, `locked_reason: 'premium'|'progression'|null`. The #1 CTA + `nextModule` logic already exist.
- `ModuleCard.tsx` (module tile) and `LevelCard.tsx` — premium-locked rendering: CHECK current state (4B "wire module/level locks" may already show some premium indicator) and only add the badge/teaser where missing.
- Parent: `src/pages/ParentDashboard.tsx`, `src/components/parent/PremiumRequestsCard.tsx`, `src/components/SubscriptionCard.tsx`. `premiumApi`/parent API exposes pending requests (`child_username`, `context_kind/label`) and subscription status.

---

## File Structure
- **Create** `frontend/src/lib/premiumNudge.ts` + `__tests__/premiumNudge.test.ts`.
- **Modify** `frontend/src/api/premium.ts` — `PremiumRequestKind += 'home'`.
- **Create** `frontend/src/components/child/PremiumUpsellCard.tsx` + `__tests__/PremiumUpsellCard.test.tsx`.
- **Modify** `frontend/src/pages/child/Home.tsx` — render the upsell card for non-premium.
- **Modify** `frontend/src/pages/child/Module.tsx` + `tests/unit/child-Module.test.tsx` — earned-moment nudge.
- **Modify** `frontend/src/components/child/ModuleCard.tsx` and/or `LevelCard.tsx` (+ tests) — locked-cue badges (only if missing).
- **Modify** `frontend/src/pages/ParentDashboard.tsx` (+ test) — value block + Subscribe CTA.

---

## Task 1: `premiumNudge` helper + widen request kind

**Files:** Create `frontend/src/lib/premiumNudge.ts`, `frontend/src/lib/__tests__/premiumNudge.test.ts`; Modify `frontend/src/api/premium.ts`.

- [ ] **Step 1: Failing test** — `premiumNudge.test.ts`:

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { isNudgeDismissed, dismissNudge, DISMISS_DAYS } from '@/lib/premiumNudge';

beforeEach(() => localStorage.clear());

describe('premiumNudge', () => {
  it('not dismissed by default', () => {
    expect(isNudgeDismissed('home-upsell')).toBe(false);
  });
  it('dismiss persists and reads back dismissed', () => {
    dismissNudge('home-upsell');
    expect(isNudgeDismissed('home-upsell')).toBe(true);
  });
  it(`re-appears after ${DISMISS_DAYS} days`, () => {
    dismissNudge('k');
    const future = Date.now() + (DISMISS_DAYS + 1) * 24 * 60 * 60 * 1000;
    vi.spyOn(Date, 'now').mockReturnValue(future);
    expect(isNudgeDismissed('k')).toBe(false);
    vi.restoreAllMocks();
  });
  it('treats unavailable localStorage as not-dismissed', () => {
    const spy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('nope'); });
    expect(isNudgeDismissed('k')).toBe(false);
    spy.mockRestore();
  });
});
```

- [ ] **Step 2: Run → fail** — `cd frontend && npm run test -- premiumNudge`.

- [ ] **Step 3: Implement** — `frontend/src/lib/premiumNudge.ts`:

```ts
export const DISMISS_DAYS = 7;
const KEY_PREFIX = 'ik.premiumNudge.';

export function isNudgeDismissed(key: string): boolean {
  try {
    const raw = localStorage.getItem(KEY_PREFIX + key);
    if (!raw) return false;
    const ts = Number(raw);
    if (!Number.isFinite(ts)) return false;
    return Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

export function dismissNudge(key: string): void {
  try {
    localStorage.setItem(KEY_PREFIX + key, String(Date.now()));
  } catch {
    /* storage unavailable — nudge will simply re-show; acceptable */
  }
}
```

- [ ] **Step 4: Widen the kind** — in `frontend/src/api/premium.ts` change `PremiumRequestKind` to `'module' | 'level' | 'challenge' | 'ticker' | 'coach' | 'home'`.

- [ ] **Step 5: Run → pass** — `cd frontend && npm run test -- premiumNudge`. Then `npx tsc -b` (the union change compiles).

- [ ] **Step 6: Commit**

```bash
cd /Users/leeashmore/investikid
git add frontend/src/lib/premiumNudge.ts frontend/src/lib/__tests__/premiumNudge.test.ts frontend/src/api/premium.ts
git commit -m "$(cat <<'EOF'
feat(premium): premiumNudge dismiss/cap helper + 'home' request kind

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Child Home upsell card

**Files:** Create `frontend/src/components/child/PremiumUpsellCard.tsx` + `__tests__/PremiumUpsellCard.test.tsx`; Modify `frontend/src/pages/child/Home.tsx`.

- [ ] **Step 1: Failing test** — `PremiumUpsellCard.test.tsx`. Mock `usePremiumPaywall` (capture `open`) and `premiumNudge`. The component takes `isPremium: boolean` as a prop (Home passes the real value, keeping the component pure/testable). Assert:
  - `isPremium={true}` → renders nothing (`container` empty).
  - `isPremium={false}` + not dismissed → shows `PAYWALL_TITLE` + at least one benefit + an "Ask my grown-up" button + a dismiss button.
  - clicking "Ask my grown-up" calls `open({kind:'home', label:'Premium'})`.
  - clicking dismiss calls `dismissNudge('home-upsell')` and the card disappears.
  - dismissed (mock `isNudgeDismissed→true`) → renders nothing.
  - axe-clean.

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';

const open = vi.fn();
vi.mock('@/hooks/usePremiumPaywall', () => ({ usePremiumPaywall: () => ({ open }) }));
vi.mock('@/lib/premiumNudge', () => ({
  isNudgeDismissed: vi.fn(() => false),
  dismissNudge: vi.fn(),
}));
import { isNudgeDismissed, dismissNudge } from '@/lib/premiumNudge';
import { PremiumUpsellCard } from '../PremiumUpsellCard';

beforeEach(() => { vi.clearAllMocks(); vi.mocked(isNudgeDismissed).mockReturnValue(false); });

describe('PremiumUpsellCard', () => {
  it('hidden for premium users', () => {
    const { container } = render(<PremiumUpsellCard isPremium />);
    expect(container).toBeEmptyDOMElement();
  });
  it('hidden when dismissed', () => {
    vi.mocked(isNudgeDismissed).mockReturnValue(true);
    const { container } = render(<PremiumUpsellCard isPremium={false} />);
    expect(container).toBeEmptyDOMElement();
  });
  it('shows for non-premium and asks via the paywall', async () => {
    render(<PremiumUpsellCard isPremium={false} />);
    await userEvent.click(screen.getByRole('button', { name: /ask my grown-up|unlock/i }));
    expect(open).toHaveBeenCalledWith({ kind: 'home', label: 'Premium' });
  });
  it('dismiss hides the card and persists', async () => {
    render(<PremiumUpsellCard isPremium={false} />);
    await userEvent.click(screen.getByRole('button', { name: /dismiss/i }));
    expect(dismissNudge).toHaveBeenCalledWith('home-upsell');
    expect(screen.queryByText(/premium/i)).toBeNull();
  });
  it('no axe violations', async () => {
    const { container } = render(<PremiumUpsellCard isPremium={false} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run → fail**.

- [ ] **Step 3: Implement** `PremiumUpsellCard.tsx`:

```tsx
import { useState } from 'react';
import { Sparkles, X } from 'lucide-react';
import { usePremiumPaywall } from '@/hooks/usePremiumPaywall';
import { isNudgeDismissed, dismissNudge } from '@/lib/premiumNudge';
import { PREMIUM_BENEFITS } from '@/lib/premiumConfig';

const KEY = 'home-upsell';

export function PremiumUpsellCard({ isPremium }: { isPremium: boolean }) {
  const { open } = usePremiumPaywall();
  const [hidden, setHidden] = useState(() => isNudgeDismissed(KEY));
  if (isPremium || hidden) return null;
  return (
    <div className="relative rounded-2xl border-2 border-accent-200 bg-accent-50 p-4">
      <button
        type="button"
        onClick={() => { dismissNudge(KEY); setHidden(true); }}
        aria-label="Dismiss"
        className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full text-accent-700 hover:bg-accent-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent-500"
      >
        <X className="h-4 w-4" aria-hidden="true" />
      </button>
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-accent-600" aria-hidden="true" />
        <h2 className="text-base font-bold text-gray-900">Unlock Premium 🌟</h2>
      </div>
      <ul className="mt-2 space-y-1 text-sm text-gray-700">
        {PREMIUM_BENEFITS.slice(0, 2).map((b) => (
          <li key={b} className="flex items-center gap-1.5"><span aria-hidden="true">✨</span>{b}</li>
        ))}
      </ul>
      <button
        type="button"
        onClick={() => open({ kind: 'home', label: 'Premium' })}
        className="mt-3 inline-flex min-h-[44px] items-center rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
      >
        Ask my grown-up
      </button>
    </div>
  );
}
```

(Confirm `accent-*` tokens exist — `PremiumBadge` uses `accent-100/700`; if `accent-50/200/500/600` are missing, substitute the nearest existing accent/brand shades.)

- [ ] **Step 4: Wire into Home** — in `Home.tsx`, import `PremiumUpsellCard`, determine `isPremium` from the existing client source (the `['me']` query / premium context 4B uses — reuse it; do not add a new fetch), and render `<PremiumUpsellCard isPremium={isPremium} />` below `<LevelProgressCard .../>`.

- [ ] **Step 5: Run → pass** — `npm run test -- PremiumUpsellCard Home`; `npx tsc -b`.

- [ ] **Step 6: Commit** (`git add` the new component + test + `Home.tsx`).

---

## Task 3: "Earned moment" nudge (Module page)

**Files:** Modify `frontend/src/pages/child/Module.tsx`; Modify `frontend/tests/unit/child-Module.test.tsx`.

- [ ] **Step 1: Failing test** — add to `child-Module.test.tsx` (it already mocks `fetch`/levels + `usePremiumPaywall` via `PremiumPaywallProvider`). Seed levels: Level 1 `completed`, Level 2 `completed` (both free), Level 3 `state:'locked', locked_reason:'premium'`. Assert the page shows an earned-moment nudge ("ready" / "Unlock Premium") with an "Ask my grown-up" button, and clicking it opens the paywall (`kind:'level'`). Also: a control case where the next locked level is `locked_reason:'progression'` → the earned nudge does NOT show. (Mock `premiumNudge.isNudgeDismissed→false`.)

- [ ] **Step 2: Run → fail**.

- [ ] **Step 3: Implement** in `Module.tsx`:
  - Compute `nextPremiumLevel`: the first level with `state==='locked' && locked_reason==='premium'` where every level before it is `state==='completed'`.
  - When it exists and `!isNudgeDismissed('level-nudge:'+moduleId)`, render a celebratory nudge card (brand/accent) with text like "🎉 You're ready for {nextPremiumLevel.title}! Unlock Premium to keep going 🌟", an "Ask my grown-up" button → `openPaywall({kind:'level', label: nextPremiumLevel.title})`, and a dismiss → `dismissNudge('level-nudge:'+moduleId)` + hide.
  - **Render priority:** show this nudge INSTEAD of the existing #1 "Module complete → Next module" CTA when `nextPremiumLevel` exists; otherwise keep the existing CTA exactly as-is.

- [ ] **Step 4: Run → pass** — `npm run test -- child-Module`; `npx tsc -b`.

- [ ] **Step 5: Commit** (`Module.tsx` + test).

---

## Task 4: Locked-cue badges

**Files:** Modify `frontend/src/components/child/ModuleCard.tsx` and/or `LevelCard.tsx`; their tests.

- [ ] **Step 1: Check current state** — read `ModuleCard.tsx` + `LevelCard.tsx`; determine whether a premium indicator already shows on premium-locked tiles/cards (4B may have added one). Only add what's missing.
- [ ] **Step 2: Failing test** — assert a premium-locked module tile and a premium-locked level card render the `PremiumBadge` ("✨ Premium") + a short teaser; a free one does not. (Use the components' existing test harness.)
- [ ] **Step 3: Implement** — render `<PremiumBadge />` + a one-line teaser ("Unlock to continue") when the module/level is premium-locked (`is_premium` && locked / `locked_reason==='premium'`). Keep tap-to-paywall behaviour unchanged. Use existing tokens.
- [ ] **Step 4: Run → pass**; `npx tsc -b`.
- [ ] **Step 5: Commit.**

(If the badge is already present in both places, this task reduces to adding the teaser + a regression test — note that in the commit.)

---

## Task 5: Parent value block + Subscribe CTA

**Files:** Modify `frontend/src/pages/ParentDashboard.tsx` (+ test).

- [ ] **Step 1: Failing test** — for a **non-subscribed** parent, the dashboard shows a "Premium gives your child" value block (≥1 `PREMIUM_BENEFITS` item) + a Subscribe CTA; when a pending premium request exists, it's highlighted ("{child} asked to unlock Premium"). For a **subscribed** parent, the upsell block is not shown (normal subscription management only). Mirror the existing `ParentDashboard`/`PremiumRequestsCard`/`SubscriptionCard` test harness + how subscription status + pending requests are sourced.
- [ ] **Step 2: Run → fail**.
- [ ] **Step 3: Implement** — add the value block + Subscribe CTA near `PremiumRequestsCard`/`SubscriptionCard`, gated on `!subscribed`. Reuse `SubscriptionCard`'s subscribe action (don't reimplement billing). Highlight pending request copy using the existing requests data.
- [ ] **Step 4: Run → pass**; `npx tsc -b`.
- [ ] **Step 5: Commit.**

---

## Task 6: Full regression + close-out

**Files:** none (verification only).

- [ ] **Step 1: Frontend gate** — `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`.
- [ ] **Step 2: Push + report** — `cd /Users/leeashmore/investikid && git push origin testing`; report CI. Do NOT promote. Leave unrelated files alone.

---

## Self-Review

**1. Spec coverage:** A Home upsell → Task 2 ; B earned-moment → Task 3 ; C parent value/CTA → Task 5 ; D locked cues → Task 4 ; dismiss/cap helper + 'home' kind → Task 1. All gentle/dismissible/capped; kids only open the paywall (parent decides). ✓

**2. Placeholder scan:** Helper + upsell card code complete; nudge + parent + badge tasks point at named existing files/harnesses with concrete assertions. "Confirm is_premium source" / "check current badge state" are deliberate reuse checks, not vague gaps. ✓

**3. Type consistency:** `PremiumRequestKind` widened once (Task 1) and used as `'home'` (Task 2) / `'level'` (Task 3); `open({kind,label})` matches `usePremiumPaywall`; `premiumNudge` keys: `'home-upsell'`, `'level-nudge:'+moduleId`. `PremiumUpsellCard({isPremium})` consistent between component, test, and Home wiring. ✓
