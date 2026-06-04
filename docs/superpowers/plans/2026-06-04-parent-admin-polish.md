# SP-E — Parent / Admin Sky-Blue + Penny Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the parent dashboard and admin panel onto the sky-blue/Penny identity (parent: Penny header + polish; admin: dark→light theme conversion) — layout-only, no behaviour change.

**Architecture:** Pure restyle reusing existing semantic tokens. Parent dashboard gets the `Penny` mascot + wordmark and tidied states. The admin panel's dark slate theme is converted to the light card aesthetic via one consistent dark→light class mapping applied across all 18 admin files, shell-first. No API/data/route/behaviour changes.

**Tech Stack:** React 18 + Vite + TS + TanStack Query + Tailwind v4 (CSS-first `@theme`) + shadcn/ui; Vitest + vitest-axe.

---

## Reference facts (verified — read before starting)

- **Spec:** `invest-ed/docs/superpowers/specs/2026-06-04-parent-admin-polish-design.md`. This is **layout-only** — never change a route, API call, query/mutation, data shape, admin CRUD behaviour, or auth guard. Only class names / mascot / copy.
- **Token vocabulary** (from `src/index.css @theme`; map dark→light using these):
  - Page background: `bg-background` (= `surface` `#f0f9ff`, a light sky tint) — or `bg-surface`. Cards: `bg-card` (`#ffffff`). 
  - Text: headings `text-foreground` (= `ink` `#0f172a`) or `text-ink`; muted/body `text-muted-foreground` (`#475569`, AA on white & on surface).
  - Borders: `border-border` (= `line` `#bae6fd`) / `border-line`; inputs `border-input`.
  - Brand: `brand-50…900`; active nav / primary accents use `bg-brand-gradient` (the sky→blue→indigo gradient utility) or `bg-brand-600`; hover wash `hover:bg-brand-50`.
- **Dark→light mapping (apply uniformly):**
  | Dark (remove) | Light (use) |
  |---|---|
  | `bg-slate-950` (page) | `bg-background` |
  | `bg-slate-900` (card/sidebar) | `bg-card` |
  | `border-slate-700` / `-800` | `border-line` |
  | `text-slate-50` / `-100` | `text-foreground` |
  | `text-slate-300/400/500` | `text-muted-foreground` |
  | `bg-blue-600` (active/primary) | `bg-brand-gradient` (nav active) / `bg-brand-600` (button) |
  | `hover:bg-slate-800` | `hover:bg-brand-50` |
  | `text-blue-400` (stray) | `text-brand-600` (or correct semantic) |
  | dark input styles | `border border-input bg-background text-base` |
- **`Penny`** mascot: `import { Penny } from '@/components/child/ui/Penny'`; props `{ size?: number; mood?: 'happy'|'thinking'|'excited'; className?: string }`; already renders `aria-hidden`. Branded header pattern (from `src/components/AuthPage.tsx`): `<Penny size={36} mood="happy" />` next to `<span className="text-xl font-extrabold tracking-tight text-ink">InvestiKid</span>`.
- **Admin tests do NOT assert on `slate-*`/`blue-*` classes** (verified by grep over `src/components/admin/__tests__/`). They assert roles/text/behaviour, so class changes should not break them. Run them anyway after each task.
- **Admin shell files:** `AdminLayout.tsx` (`bg-slate-950`, `text-slate-400` loading), `AdminSidebar.tsx` (`bg-slate-900`, `border-slate-700`, active `bg-blue-600`, hover `bg-slate-800`, emoji nav — KEEP emoji), `AdminDashboard.tsx` (`bg-slate-900` cards, `border-slate-700`, `text-slate-50/500`, one stray `text-blue-400`).
- **Parent dashboard** (`src/pages/ParentDashboard.tsx`): the header has a gradient **"IE" monogram** `<Link to="/parent" className="flex h-8 w-8 …bg-brand-gradient…">IE</Link>` + `<h1>Parent Dashboard</h1>`. Empty state at ~line 76-80; loading ~68; `ErrorBanner` ~69-75. `ChildCard`/`SubscriptionCard`/`SignInMethods` already branded — DO NOT touch.

## Commands (run from `invest-ed/frontend`)

- `npx tsc -b` · `npm run lint` (known-OK warnings: `button.tsx` + `Market.tsx` react-refresh — warnings, not errors) · `npm test` · `npm run build`.
- Git from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. NEVER read/modify any `.env`. Web-only (no `npx cap sync ios`).

---

## Task 1: Parent dashboard — Penny header + polish

**Files:**
- Modify: `invest-ed/frontend/src/pages/ParentDashboard.tsx`

- [ ] **Step 1: Confirm baseline tests pass**

Run: `cd invest-ed/frontend && npm test -- ParentDashboard 2>/dev/null; npx tsc -b`
Expected: tsc clean. (If no ParentDashboard test file exists, that's fine — tsc is the gate.)

- [ ] **Step 2: Add the Penny import**

In `src/pages/ParentDashboard.tsx`, add to the imports:
```tsx
import { Penny } from '@/components/child/ui/Penny';
```

- [ ] **Step 3: Replace the "IE" monogram with Penny + wordmark**

Replace the header's left cluster (the `<Link to="/parent" …>IE</Link>` + `<h1>` block, lines ~50-55) with:
```tsx
        <div className="flex items-center gap-2">
          <Link to="/parent" className="flex items-center gap-2" aria-label="InvestiKid parent home">
            <Penny size={32} mood="happy" />
            <span className="text-lg font-extrabold tracking-tight text-ink sm:text-xl">InvestiKid</span>
          </Link>
          <h1 className="sr-only">Parent Dashboard</h1>
        </div>
```
(The visible page title role moves to the brand wordmark; the `<h1>` is preserved for screen readers / document outline. If you prefer the visible "Parent Dashboard" heading kept, instead render it after the wordmark as `<span className="hidden text-lg font-semibold text-muted-foreground sm:inline">Parent Dashboard</span>` and keep an `<h1 className="sr-only">`. Pick the first form.)

- [ ] **Step 4: Warm the empty state**

Replace the empty-state paragraph (`No children linked to this account.`) with a slightly warmer, still-factual line:
```tsx
        <p className="mt-6 text-sm text-muted-foreground">
          No children linked to this account yet — once a child signs up with your email, they'll appear here.
        </p>
```
Leave the loading line and `ErrorBanner` as-is (roles unchanged); only adjust spacing if visibly off.

- [ ] **Step 5: Verify**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except the two known warnings; tests pass; build OK.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/pages/ParentDashboard.tsx
git commit -m "feat(sp-e): Penny + wordmark header and friendlier empty state on parent dashboard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Admin shell — Layout + Sidebar + Dashboard (light theme)

**Files:**
- Modify: `invest-ed/frontend/src/components/admin/AdminLayout.tsx`
- Modify: `invest-ed/frontend/src/components/admin/AdminSidebar.tsx`
- Modify: `invest-ed/frontend/src/components/admin/AdminDashboard.tsx`
- Tests (must stay green): `src/components/admin/__tests__/AdminLayout.test.tsx`, `AdminDashboard.test.tsx`

- [ ] **Step 1: Run the shell tests (baseline green)**

Run: `cd invest-ed/frontend && npm test -- AdminLayout AdminDashboard`
Expected: PASS (they assert behaviour/text, not colours).

- [ ] **Step 2: Convert `AdminLayout.tsx`**

Replace the dark wrappers:
```tsx
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <span className="text-muted-foreground">Loading…</span>
      </div>
    );
  }
  // ...
  return (
    <div className="flex min-h-screen bg-background">
      <AdminSidebar />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
```
(Only the two `bg-slate-950` → `bg-background` and `text-slate-400` → `text-muted-foreground` swaps; logic/guards unchanged.)

- [ ] **Step 3: Convert `AdminSidebar.tsx`**

```tsx
    <aside className="flex w-52 flex-col border-r border-line bg-card p-4">
      <div className="mb-6 text-lg font-extrabold text-ink">📚 InvestiKid Admin</div>
      <nav className="flex flex-col gap-1" aria-label="Admin navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm font-medium ${
                isActive
                  ? 'bg-brand-gradient text-white'
                  : 'text-muted-foreground hover:bg-brand-50 hover:text-ink'
              }`
            }
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-line pt-4">
        <a href="/" className="text-sm text-muted-foreground hover:text-ink">← Back to App</a>
      </div>
    </aside>
```
(Emoji nav kept. Active item uses `bg-brand-gradient`.)

- [ ] **Step 4: Convert `AdminDashboard.tsx`**

Headings/cards to light; fix the stray `text-blue-400`:
```tsx
const CARDS = [
  { key: 'modules' as const, label: 'Modules', icon: '📖', color: 'text-success-600' },
  { key: 'lessons' as const, label: 'Lessons', icon: '📝', color: 'text-brand-600' },
  { key: 'badges' as const, label: 'Badges', icon: '🏆', color: 'text-accent-600' },
  { key: 'challenges' as const, label: 'Challenges', icon: '⚡', color: 'text-accent-600' },
];
```
```tsx
      <h2 className="mb-2 text-xl font-semibold text-ink">Dashboard</h2>
      <p className="mb-6 text-sm text-muted-foreground">Content overview</p>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map((card) => (
          <div key={card.key} className="rounded-2xl border border-line bg-card p-5 shadow-sm">
            <div className="text-sm text-muted-foreground">{card.icon} {card.label}</div>
            <div className="mt-1 text-3xl font-bold text-ink">
              {isLoading ? '—' : stats?.[card.key] ?? 0}
            </div>
          </div>
        ))}
      </div>
```
(The `color` field is currently unused for rendering in this component — keep it consistent/semantic; if it is genuinely unused, leave the array values semantic as above rather than introducing new usage.)

- [ ] **Step 5: Verify shell**

Run: `cd invest-ed/frontend && npx tsc -b && npm test -- AdminLayout AdminDashboard AdminSidebar`
Expected: tsc clean; tests pass.

- [ ] **Step 6: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/AdminLayout.tsx invest-ed/frontend/src/components/admin/AdminSidebar.tsx invest-ed/frontend/src/components/admin/AdminDashboard.tsx
git commit -m "feat(sp-e): convert admin shell (layout/sidebar/dashboard) to light sky-blue

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Admin lists + settings (light theme)

**Files:**
- Modify: `ModuleList.tsx`, `LevelList.tsx`, `LevelLessonList.tsx`, `BadgeList.tsx`, `ChallengeList.tsx`, `FeedbackList.tsx`, `ModuleEngagement.tsx`, `AdminSettings.tsx` (all under `invest-ed/frontend/src/components/admin/`)
- Tests (stay green): `ModuleList.test.tsx`, `LevelList.test.tsx`, `BadgeList.test.tsx`, `ChallengeList.test.tsx`, `ModuleEngagement.test.tsx`, `AdminSettings.test.tsx`

- [ ] **Step 1: Baseline tests**

Run: `cd invest-ed/frontend && npm test -- ModuleList LevelList BadgeList ChallengeList ModuleEngagement AdminSettings`
Expected: PASS.

- [ ] **Step 2: Apply the dark→light mapping to each list/settings file**

For each file, READ it first, then substitute every dark class per the mapping table in Reference facts:
- `bg-slate-900` → `bg-card`; container/page `bg-slate-950` → `bg-background`.
- `border-slate-700/800` → `border-line`.
- `text-slate-50/100` → `text-ink`; `text-slate-300/400/500` → `text-muted-foreground`.
- `bg-blue-600`/primary buttons → `bg-brand-600 text-white` (or existing `Button` component if used).
- `hover:bg-slate-800` → `hover:bg-brand-50`.
- Any `text-blue-400` → `text-brand-600`.
- Keep structure, props, handlers, and any list semantics identical. Do not alter `OrderArrows`/`ConfirmDialog` usage (Task 5).

- [ ] **Step 3: Verify after each file (or as a batch)**

Run: `cd invest-ed/frontend && npx tsc -b && npm test -- ModuleList LevelList LevelLessonList BadgeList ChallengeList FeedbackList ModuleEngagement AdminSettings`
Expected: tsc clean; tests pass. Visually confirm no remaining `slate-`/`bg-blue-6` in these files: `grep -rE "slate-|bg-blue-6|text-blue-4" src/components/admin/{ModuleList,LevelList,LevelLessonList,BadgeList,ChallengeList,FeedbackList,ModuleEngagement,AdminSettings}.tsx` → no output.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/ModuleList.tsx invest-ed/frontend/src/components/admin/LevelList.tsx invest-ed/frontend/src/components/admin/LevelLessonList.tsx invest-ed/frontend/src/components/admin/BadgeList.tsx invest-ed/frontend/src/components/admin/ChallengeList.tsx invest-ed/frontend/src/components/admin/FeedbackList.tsx invest-ed/frontend/src/components/admin/ModuleEngagement.tsx invest-ed/frontend/src/components/admin/AdminSettings.tsx
git commit -m "feat(sp-e): convert admin lists + settings to light sky-blue

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Admin forms (light theme) — the bulk

**Files:**
- Modify: `ModuleForm.tsx`, `LessonForm.tsx`, `BadgeForm.tsx`, `ChallengeForm.tsx`, `LevelForm.tsx` (under `invest-ed/frontend/src/components/admin/`)
- Tests (stay green): `ModuleForm.test.tsx`, `LessonForm.test.tsx`, `LevelForm.test.tsx`

- [ ] **Step 1: Baseline tests**

Run: `cd invest-ed/frontend && npm test -- ModuleForm LessonForm LevelForm`
Expected: PASS.

- [ ] **Step 2: Convert the forms (read each first)**

These are the heaviest (LessonForm ~58, ModuleForm ~51, ChallengeForm ~42, LevelForm ~32, BadgeForm ~27 dark hits). Apply the mapping, with form-specific attention:
- Inputs/selects/textareas: dark field styles → the app's standard light input: `border border-input bg-background text-base text-ink placeholder:text-muted-foreground focus:ring-2 focus:ring-brand-300` (keep existing sizing; ensure `text-base` so fields are ≥16px).
- Labels: `text-slate-300/400` → `text-ink` (or `text-muted-foreground` for hints).
- Field containers/cards: `bg-slate-900` → `bg-card`, `border-slate-700` → `border-line`.
- Primary/submit buttons: `bg-blue-600` → `bg-brand-600 text-white` (or the shared `Button`).
- Error/validation text stays its semantic colour (`text-danger-600`); do not weaken it.
- Preserve every field name, `value`/`onChange`, validation, and submit handler exactly.

- [ ] **Step 3: Verify**

Run: `cd invest-ed/frontend && npx tsc -b && npm test -- ModuleForm LessonForm BadgeForm ChallengeForm LevelForm`
Expected: tsc clean; tests pass. Confirm no leftovers: `grep -rE "slate-|bg-blue-6|text-blue-4" src/components/admin/{ModuleForm,LessonForm,BadgeForm,ChallengeForm,LevelForm}.tsx` → no output.

- [ ] **Step 4: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/ModuleForm.tsx invest-ed/frontend/src/components/admin/LessonForm.tsx invest-ed/frontend/src/components/admin/BadgeForm.tsx invest-ed/frontend/src/components/admin/ChallengeForm.tsx invest-ed/frontend/src/components/admin/LevelForm.tsx
git commit -m "feat(sp-e): convert admin forms to light sky-blue inputs

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Admin shared (ConfirmDialog + OrderArrows) + a11y/contrast pass + regression

**Files:**
- Modify: `invest-ed/frontend/src/components/admin/ConfirmDialog.tsx`, `OrderArrows.tsx`
- Test (stay green): `ConfirmDialog.test.tsx`, `OrderArrows.test.tsx`
- Possibly modify: an admin shell test to add a `vitest-axe` assertion (see Step 3)

- [ ] **Step 1: Convert the two shared components**

Apply the mapping to `ConfirmDialog.tsx` (7 dark hits: dialog surface `bg-slate-900`→`bg-card`, `border-slate-700`→`border-line`, text → `text-ink`/`text-muted-foreground`, destructive action keeps `bg-danger-600`/`text-white`) and `OrderArrows.tsx` (4 hits: button `text-slate-400 hover:text-slate-200` → `text-muted-foreground hover:text-ink`, disabled state preserved). Keep all `onClick`/`disabled`/`aria-label` props.

- [ ] **Step 2: Confirm no dark classes remain anywhere in admin**

Run: `cd invest-ed/frontend && grep -rE "slate-|bg-blue-[5-9]|text-blue-4" src/components/admin/*.tsx || echo "ADMIN FULLY CONVERTED"`
Expected: `ADMIN FULLY CONVERTED` (no matches in non-test admin files).

- [ ] **Step 3: Add a contrast/a11y guard on the shell**

In `src/components/admin/__tests__/AdminDashboard.test.tsx` (or AdminLayout's), add a `vitest-axe` assertion if one isn't present, mirroring how sibling tests use it:
```tsx
import { axe } from 'vitest-axe';
// inside a test:
const { container } = render(/* existing AdminDashboard render */);
expect(await axe(container)).toHaveNoViolations();
```
(Match the repo's existing axe setup/imports. If the test already runs axe, just confirm it still passes on the light theme.)

- [ ] **Step 4: Full regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: tsc clean; lint clean except the two known warnings; ALL tests pass; build OK.

- [ ] **Step 5: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/components/admin/ConfirmDialog.tsx invest-ed/frontend/src/components/admin/OrderArrows.tsx invest-ed/frontend/src/components/admin/__tests__/AdminDashboard.test.tsx
git commit -m "feat(sp-e): convert admin shared components + add admin a11y guard

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Docs + push + green CI

**Files:**
- Modify: `invest-ed/docs/superpowers/PROGRESS.md`, `invest-ed/AGENTS.md`

- [ ] **Step 1: Final whole-app regression**

Run: `cd invest-ed/frontend && npx tsc -b && npm run lint && npm test && npm run build`
Expected: all green (two known warnings only).

- [ ] **Step 2: Update docs**

In `invest-ed/docs/superpowers/PROGRESS.md`: mark **SP-E** ✅ shipped (parent dashboard Penny header + polish; admin panel converted dark→light sky-blue across all 18 files) and note the rebrand programme is **complete** (SP-0/A/B/C/D1/D2/F + Country switcher + SP-E all shipped). Move the "Resume here" pointer to the standing user-only items (iOS device rebuild, OAuth setup, App Store display name). Mirror in `invest-ed/AGENTS.md` "▶ Current work".

- [ ] **Step 3: Commit docs**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/docs/superpowers/PROGRESS.md invest-ed/AGENTS.md
git commit -m "docs(sp-e): mark SP-E shipped; rebrand programme complete

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: Push + watch CI**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```
Confirm all 6 CI jobs go green (frontend, backend, security, a11y, responsive, iOS Capacitor).

---

## Self-review notes

- **Spec coverage:** Workstream A (Penny header + wordmark, warmer empty state, ParentDashboard only) → Task 1. Workstream B mapping across all 18 admin files → shell (T2), lists+settings (T3), forms (T4), shared (T5). Emoji nav kept (T2). WCAG/contrast via vitest-axe on the shell (T5). Testing (keep 13 admin tests green, tsc/lint/test/build, CI) → every task + T6. Docs/close-out → T6.
- **Placeholder scan:** mapping table + exact code given for parent header and shell; lists/forms use the explicit mapping with per-file "read first" (the substitution is mechanical and identical per the table) — acceptable for a uniform restyle rather than re-listing every line of 13 files.
- **Consistency:** token names (`bg-background`, `bg-card`, `text-ink`, `text-muted-foreground`, `border-line`, `border-input`, `bg-brand-gradient`, `bg-brand-600`, `hover:bg-brand-50`) used identically across all tasks. `Penny` import path and props consistent with AuthPage.
- **Risk note:** admin tests don't assert colour classes (verified), so the conversion shouldn't break them — but each task re-runs the relevant tests to be sure.
