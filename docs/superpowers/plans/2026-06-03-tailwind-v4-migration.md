# Tailwind v4 Migration + iOS 17 Floor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `invest-ed/frontend` from Tailwind CSS v3.4 to v4 (CSS-first config) and raise the iOS deployment target to 17.0, with **zero intended visual or behavioural change**.

**Architecture:** Move Tailwind out of the PostCSS chain onto the official `@tailwindcss/vite` plugin; replace the three `@tailwind` directives with `@import "tailwindcss"`; relocate the design tokens from `tailwind.config.js` into a CSS `@theme` block keeping the **exact same HSL values**; swap `tailwindcss-animate` → `tw-animate-css`; preserve every `@layer base` rule verbatim. Verification is build + lint + full test suite + before/after screenshot parity (not new unit tests — this is config).

**Tech Stack:** Tailwind CSS v4, `@tailwindcss/vite`, `tw-animate-css`, Vite 6, React 18, Capacitor iOS.

**Spec:** `docs/superpowers/specs/2026-06-03-tailwind-v4-migration-design.md`

**Conventions:** All frontend commands run from `invest-ed/frontend`. Git runs from repo root `/Users/leeashmore/Local Repo`; commit to `main`; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway deploys backend **only on green CI** (5 jobs: frontend, backend, security, a11y, responsive). Backend is untouched in this sub-project. The lint baseline has **one expected pre-existing warning** in `src/components/ui/button.tsx` (fast-refresh) — 0 errors otherwise.

**Audit facts (verified, so steps are concrete):**
- No bare `ring` class exists; all ring usages are width-pinned (`ring-2`/`ring-1`/`ring-0`) or colour-specific (`ring-ring`, `ring-blue-500`, `ring-amber-*`, `ring-offset-2`, `ring-offset-background`). v4's ring-width default change (3px→1px) therefore does not affect rendering.
- Animate utilities in use (`animate-in`, `animate-out`, `fade-in-0`, `fade-out-0`, `fade-out-80`, `zoom-in-95`, `zoom-out-95`, `slide-in-from-*`, `slide-out-to-*`) all come from `tailwindcss-animate`; `tw-animate-css` provides the same class names.
- v4's default border-colour change (`gray-200`→`currentColor`) is pre-neutralised by the existing `* { @apply border-border }` rule.
- `src/main.tsx:6` imports `./index.css`. `darkMode: ['class']` is configured but the app defines no `.dark` token block (dark mode effectively unused; preserve the class variant anyway).

---

### Task 1: Establish a clean baseline + parity screenshots

Capture the "before" state so the migration's zero-visual-change goal is verifiable. No app code changes.

**Files:**
- Create (temporary, NOT committed): `invest-ed/frontend/tmp-parity.mjs`
- Output dir: `/tmp/tw-parity/before/` and later `/tmp/tw-parity/after/`

- [ ] **Step 1: Confirm green baseline on current v3**

Run (from `invest-ed/frontend`):
```bash
npx tsc -b && npm run lint && npm test && npm run build
```
Expected: tsc clean; lint shows only the `button.tsx` fast-refresh warning (0 errors); vitest all green; build succeeds. If anything else fails, STOP — the tree is not clean; report before proceeding.

- [ ] **Step 2: Write the parity screenshot script**

Create `invest-ed/frontend/tmp-parity.mjs` (drives the dev server with a mocked API so the child screens render without a backend). `OUTDIR` is taken from `process.env.OUTDIR`:

```js
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const BASE = 'http://localhost:5188';
const OUT = process.env.OUTDIR || '/tmp/tw-parity/before';
mkdirSync(OUT, { recursive: true });

const me = { id: 'u1', email: 'maya@example.com', username: 'Maya', dob: '2015-01-01', country_code: 'GB', currency_code: 'GBP', topic_path: null, is_premium: true, is_admin: false, parent_email: 'p@example.com', created_at: '2026-01-01T00:00:00Z', email_verified_at: '2026-01-02T00:00:00Z' };
const progress = { xp: 340, level: 4, streak_count: 5, last_activity_date: '2026-06-03' };
const modules = [
  { id: 'm1', topic: 'savings', title: 'Saving Smarts', country_codes: ['GB'], is_premium: false, order_index: 0, icon: '🐷', locked: false },
  { id: 'm2', topic: 'budgeting', title: 'Budget Boss', country_codes: ['GB'], is_premium: false, order_index: 1, icon: '📊', locked: false },
  { id: 'm3', topic: 'stocks', title: 'Stock Market 101', country_codes: ['GB'], is_premium: false, order_index: 2, icon: '📈', locked: false },
  { id: 'm4', topic: 'crypto', title: 'Crypto Curious', country_codes: ['GB'], is_premium: true, order_index: 3, icon: '🪙', locked: true },
];
const recs = { continue_learning: [{ module_id: 'm1', title: 'Saving Smarts', reason: 'Pick up where you left off', mode: 'continue' }], something_new: [{ module_id: 'm3', title: 'Stock Market 101', reason: 'Try something new', mode: 'start' }], review_summary: { due_count: 3 } };
const levels = [{ id: 'l1', module_id: 'm1', title: 'Level 1 — Basics', order_index: 0, is_premium: false, icon: '⭐', state: 'in_progress', locked_reason: null, passed: false, lessons_total: 3, lessons_completed: 1 }];
const levelLessons = [
  { id: 'ls1', type: 'card', title: 'What is saving?', xp_reward: 10, order_index: 0, completed: true },
  { id: 'ls2', type: 'quiz', title: 'Saving vs spending', xp_reward: 15, order_index: 1, completed: false },
  { id: 'ls3', type: 'scenario', title: 'The piggy bank choice', xp_reward: 20, order_index: 2, completed: false },
];
const quizLesson = { id: 'ls2', module_id: 'm1', type: 'quiz', content_json: { question: 'Which is the smartest way to reach a savings goal?', choices: ['Spend it all right now', 'Set aside a little each week', 'Wait and hope it appears', 'Borrow from a friend'], answer_index: 1, explanation: "Saving a little regularly really adds up!" }, xp_reward: 15, order_index: 1, completed: false, locked: false };
const greeting = { greeting: "Hi Maya! Nice 5-day streak — let's keep it going." };

const j = (route, body) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await page.route('**/*', (route) => {
  const p = new URL(route.request().url()).pathname;
  if (p === '/users/me') return j(route, me);
  if (p === '/users/me/progress') return j(route, progress);
  if (p === '/users/me/badges') return j(route, []);
  if (p === '/modules') return j(route, modules);
  if (p === '/recommendations') return j(route, recs);
  if (p === '/profile/mastery') return j(route, { topics: [], weak_concepts: [] });
  if (p === '/profile/strengths') return j(route, { strengths: [], gaps: [] });
  if (p === '/home-greeting') return j(route, greeting);
  if (p === '/leaderboard') return j(route, []);
  if (/^\/modules\/m1\/levels$/.test(p)) return j(route, levels);
  if (/^\/levels\/l1\/lessons$/.test(p)) return j(route, levelLessons);
  if (/^\/lessons\/ls2$/.test(p)) return j(route, quizLesson);
  if (/^\/lessons\/.+\/(view|complete|practice)$/.test(p)) return j(route, { ok: true });
  return route.continue();
});
await ctx.addCookies([{ name: 'csrf_token', value: 'test', domain: 'localhost', path: '/' }]);
await page.goto(`${BASE}/home`, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}/01-home.png`, fullPage: true });
await page.goto(`${BASE}/lessons/m1/l1/ls2`, { waitUntil: 'networkidle' });
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/02-quiz.png`, fullPage: true });
await browser.close();
console.log('captured to', OUT);
```

- [ ] **Step 3: Capture BEFORE screenshots on v3**

Run (from `invest-ed/frontend`):
```bash
(npm run dev -- --port 5188 --strictPort &) ; \
  for i in $(seq 1 30); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/tw-parity/before node tmp-parity.mjs ; \
  pkill -f "port 5188"
```
Expected: `captured to /tmp/tw-parity/before` and two PNGs in that dir. View them (Read tool) to confirm they render the amber Home + quiz as expected. These are the reference for Task 5.

- [ ] **Step 4: Commit (script is gitignored / not added)**

No commit needed — this task produces only the temp script and `/tmp` images. Confirm `git status` shows `tmp-parity.mjs` as untracked and do NOT add it.

---

### Task 2: Raise iOS deployment target to 17.0

Independent of the Tailwind work; do it first so it can land/verify on its own.

**Files:**
- Modify: `invest-ed/frontend/ios/App/App.xcodeproj/project.pbxproj` (4 occurrences of `IPHONEOS_DEPLOYMENT_TARGET = 15.0;`)

- [ ] **Step 1: Replace all four deployment-target lines**

Run (from `invest-ed/frontend`):
```bash
sed -i '' 's/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/IPHONEOS_DEPLOYMENT_TARGET = 17.0;/g' ios/App/App.xcodeproj/project.pbxproj
grep -c "IPHONEOS_DEPLOYMENT_TARGET = 17.0;" ios/App/App.xcodeproj/project.pbxproj
```
Expected: prints `4`. Then confirm none remain at 15.0:
```bash
grep -c "IPHONEOS_DEPLOYMENT_TARGET = 15.0;" ios/App/App.xcodeproj/project.pbxproj
```
Expected: prints `0`.

- [ ] **Step 2: Verify Capacitor sync still succeeds**

Run (from `invest-ed/frontend`):
```bash
npx cap sync ios
```
Expected: completes without error (`✔ Sync finished`). (If CocoaPods is unavailable in the environment, the web-asset copy step still runs; note any pod warning but the pbxproj edit is the deliverable.)

- [ ] **Step 3: Commit**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/ios/App/App.xcodeproj/project.pbxproj
git commit -m "build(ios): raise deployment target to iOS 17.0

Required baseline for the Tailwind v4 upgrade (v4 targets Safari/iOS 16.4+).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Switch the toolchain to Tailwind v4

Install v4, wire the Vite plugin, drop Tailwind from PostCSS, swap the animate plugin. The app will not build cleanly until Task 4 rewrites `index.css` — so Tasks 3 and 4 land in one commit (at the end of Task 4). Do not commit at the end of Task 3.

**Files:**
- Modify: `invest-ed/frontend/package.json` (deps)
- Modify: `invest-ed/frontend/vite.config.ts`
- Delete: `invest-ed/frontend/postcss.config.js`

- [ ] **Step 1: Install v4 packages and remove v3-only ones**

Run (from `invest-ed/frontend`):
```bash
npm install tailwindcss@^4 @tailwindcss/vite@^4 tw-animate-css@latest
npm uninstall tailwindcss-animate autoprefixer
```
Expected: `tailwindcss` resolves to a 4.x version; `@tailwindcss/vite` and `tw-animate-css` are added; `tailwindcss-animate` and `autoprefixer` removed. (`postcss` may remain as a transitive dep — that's fine.)

- [ ] **Step 2: Add the Tailwind Vite plugin**

Edit `invest-ed/frontend/vite.config.ts` — add the import and register the plugin. The top of the file becomes:
```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
```
Leave the rest of the file (resolve alias, server proxy, test block) unchanged.

- [ ] **Step 3: Remove the PostCSS config (Tailwind now runs via the Vite plugin)**

Run (from `invest-ed/frontend`):
```bash
rm postcss.config.js
```
Expected: file removed. (v4 bundles autoprefixing, so the old `{ tailwindcss, autoprefixer }` PostCSS chain is obsolete.)

(No verification run here — proceed straight to Task 4; the build is expected to be broken between Step 3 and Task 4 because `index.css` still uses v3 directives.)

---

### Task 4: Rewrite `index.css` to v4 CSS-first config + delete the JS config

Relocate tokens into `@theme` with identical values; keep all base-layer rules; remove the now-unused JS config.

**Files:**
- Modify: `invest-ed/frontend/src/index.css` (full rewrite)
- Delete: `invest-ed/frontend/tailwind.config.js`

- [ ] **Step 1: Replace `src/index.css` with the v4 version**

Overwrite `invest-ed/frontend/src/index.css` with exactly:
```css
@import "tailwindcss";
@import "tw-animate-css";

/* Preserve class-based dark mode (matches the prior darkMode: ['class']). */
@custom-variant dark (&:is(.dark *));

/* Semantic design tokens — SAME HSL values as the prior v3 config.
   Mapped into Tailwind's colour/radius scales so utilities (bg-primary,
   border-border, rounded-lg, …) resolve identically. v4 ships the default
   palette (amber-*, sky-*, lime-*, …) automatically, so those keep working. */
@theme {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
}

@layer base {
  :root {
    --background: 48 100% 96%;
    --foreground: 220 9% 12%;
    --card: 0 0% 100%;
    --card-foreground: 220 9% 12%;
    --primary: 38 92% 50%;
    --primary-foreground: 0 0% 100%;
    --destructive: 0 84% 60%;
    --destructive-foreground: 0 0% 100%;
    --muted: 48 100% 93%;
    --muted-foreground: 220 9% 46%;
    --accent: 48 100% 93%;
    --accent-foreground: 220 9% 12%;
    --border: 48 97% 77%;
    --input: 48 97% 77%;
    --ring: 38 92% 35%;
    --radius: 0.75rem;
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bottom: env(safe-area-inset-bottom, 0px);
    --safe-left: env(safe-area-inset-left, 0px);
    --safe-right: env(safe-area-inset-right, 0px);
  }
  * { @apply border-border; }
  /* Prevent whole-page horizontal scroll/bleed on narrow mobile screens.
     Inner overflow-x-auto carousels are unaffected. */
  html, body, #root {
    width: 100%;
    max-width: 100%;
    overflow-x: hidden;
  }
  body { @apply bg-background text-foreground; font-family: ui-sans-serif, system-ui, sans-serif; }
  /* iOS zooms into any form field whose font-size is < 16px when it gains focus,
     and frequently does NOT zoom back out — which enlarges the layout viewport
     and pushes content off the right edge (the post-login overflow). Keep form
     controls at >=16px on touch devices to prevent the auto-zoom, without
     disabling user pinch-zoom (we must not set maximum-scale — WCAG 1.4.4). */
  @media (pointer: coarse) {
    input:not([type='checkbox']):not([type='radio']):not([type='range']),
    select,
    textarea {
      font-size: 16px !important;
    }
  }
  /* WCAG 2.2 SC 2.4.11 focus-not-obscured: keep keyboard focus clear of
     sticky TopNav (~3.5rem) + BottomTabBar (~4rem). */
  :focus-visible { scroll-margin-top: 4.5rem; scroll-margin-bottom: 5rem; }
}
```

- [ ] **Step 2: Delete the now-unused JS config**

Run (from `invest-ed/frontend`):
```bash
rm tailwind.config.js
```
Expected: removed. (v4 auto-detects content; colours/radii now live in `@theme`; `darkMode` is handled by `@custom-variant`; the only plugin, animate, is now a CSS `@import`.)

- [ ] **Step 3: Verify build + typecheck + lint**

Run (from `invest-ed/frontend`):
```bash
npm run build && npx tsc -b && npm run lint
```
Expected: build succeeds (Vite reports the Tailwind plugin active, no "unknown at-rule" or "cannot find tailwindcss" errors); tsc clean; lint shows only the `button.tsx` fast-refresh warning. If the build errors on `@tailwind`/`@apply`/`@theme`, re-check Steps in Tasks 3–4.

- [ ] **Step 4: Run the full test suite**

Run (from `invest-ed/frontend`):
```bash
npm test
```
Expected: all vitest + vitest-axe tests green (same count as the Task 1 baseline). CSS isn't evaluated in jsdom (`test.css: false`), so failures here would indicate a JS/markup regression, not styling — investigate any before continuing.

- [ ] **Step 5: Commit Tasks 3 + 4 together**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/package.json invest-ed/frontend/package-lock.json \
        invest-ed/frontend/vite.config.ts invest-ed/frontend/src/index.css
git rm invest-ed/frontend/postcss.config.js invest-ed/frontend/tailwind.config.js
git commit -m "build(frontend): migrate Tailwind CSS v3 -> v4 (CSS-first)

Switch to @tailwindcss/vite, replace @tailwind directives with
@import \"tailwindcss\", move tokens into an @theme block (identical HSL
values), swap tailwindcss-animate -> tw-animate-css, drop the PostCSS
Tailwind/autoprefixer chain and the now-unused JS config. No intended
visual change.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Verify zero visual change (screenshot parity) + neutralise any drift

**Files:**
- Uses: `invest-ed/frontend/tmp-parity.mjs` (from Task 1)
- Possibly modify: `invest-ed/frontend/src/index.css` (only if drift is found)

- [ ] **Step 1: Capture AFTER screenshots on v4**

Run (from `invest-ed/frontend`):
```bash
(npm run dev -- --port 5188 --strictPort &) ; \
  for i in $(seq 1 30); do curl -sf -o /dev/null http://localhost:5188/ && break; sleep 1; done ; \
  OUTDIR=/tmp/tw-parity/after node tmp-parity.mjs ; \
  pkill -f "port 5188"
```
Expected: two PNGs in `/tmp/tw-parity/after`.

- [ ] **Step 2: Compare before vs after**

Read both `/tmp/tw-parity/before/01-home.png` and `/tmp/tw-parity/after/01-home.png` (and the `02-quiz.png` pair) and compare visually. Expected: identical layout, colours, radii, borders, focus rings, and spacing (anti-aliasing differences are acceptable).

- [ ] **Step 3: Neutralise drift IF AND ONLY IF a difference is seen**

Only if Step 2 shows a real difference, add the targeted fix to the `@layer base` block in `src/index.css`. Likely culprits and their fixes:
  - **Borders look different (heavier/coloured):** ensure the universal rule is present (it is) — if a specific element regressed, add `*, ::before, ::after { border-color: hsl(var(--border)); }` inside `@layer base`.
  - **Default focus ring colour changed on a bare usage:** there are none in the audit, but if one appears, pin it: `@theme { --default-ring-color: hsl(var(--ring)); }`.
  - **Placeholder text colour changed (v4 preflight uses currentColor at 50% opacity):** if visibly different, add `@layer base { input::placeholder, textarea::placeholder { color: hsl(var(--muted-foreground)); opacity: 1; } }`.
If no difference is seen, make NO change and note "parity confirmed, no neutralisation needed."

- [ ] **Step 4: Re-verify after any fix**

If Step 3 changed `index.css`, re-run:
```bash
npm run build && npm run lint
```
Expected: green. Then re-capture/compare to confirm parity. If no fix was made, skip.

- [ ] **Step 5: Remove the temp parity script**

Run (from `invest-ed/frontend`):
```bash
rm -f tmp-parity.mjs
```
Confirm `git status` is clean except any intended `index.css` change from Step 3.

- [ ] **Step 6: Commit (only if Step 3 changed a file)**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/frontend/src/index.css
git commit -m "style(frontend): pin <token> to preserve v3 rendering under v4

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
If no file changed, skip this step.

---

### Task 6: Update stack docs + final regression + push

**Files:**
- Modify: `invest-ed/AGENTS.md`
- Modify: `invest-ed/.cursor/rules/frontend.mdc`
- Modify: `CLAUDE.md` (repo root)

- [ ] **Step 1: Update the three stack-description docs**

In `invest-ed/AGENTS.md`, in the `frontend/` bullet, change `Tailwind` to `Tailwind v4` and add iOS note. Find:
```
- `frontend/` — React 18 + Vite + TypeScript + TanStack Query + Tailwind + shadcn/ui, with a **Capacitor iOS** app in `frontend/ios/`. Web deployed on **Vercel**.
```
Replace `Tailwind` with `Tailwind v4 (CSS-first @theme)`.

In `invest-ed/.cursor/rules/frontend.mdc`, find the styling line:
```
- Styling: Tailwind + the design tokens in `src/index.css` (`hsl(var(--token))`) and `tailwind.config.js`.
```
Replace with:
```
- Styling: Tailwind v4 (CSS-first) + the design tokens in `src/index.css` — semantic tokens live in the `@theme` block and the `:root` HSL vars; there is no `tailwind.config.js`. Brand = an amber→orange gradient on a cream background. A matching Figma token file exists (see `AGENTS.md`).
```
(Replacing the existing styling bullet in full.)

In root `CLAUDE.md`, find:
```
- `frontend/` — React 18 + Vite + TypeScript + TanStack Query + Tailwind + shadcn/ui, with a **Capacitor iOS** app in `frontend/ios/`. Web on **Vercel**.
```
Replace `Tailwind` with `Tailwind v4`.

- [ ] **Step 2: Final full regression**

Run (from `invest-ed/frontend`):
```bash
npx tsc -b && npm run lint && npm test && npm run build && npx cap sync ios
```
Expected: tsc clean; lint = only the `button.tsx` warning; vitest green; build OK; cap sync OK.

- [ ] **Step 3: Commit docs**

```bash
cd "/Users/leeashmore/Local Repo"
git add invest-ed/AGENTS.md invest-ed/.cursor/rules/frontend.mdc CLAUDE.md
git commit -m "docs: note Tailwind v4 + iOS 17 in stack guides

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 4: Push and confirm green CI**

```bash
cd "/Users/leeashmore/Local Repo"
git push origin main
```
Then watch CI: all 5 jobs (frontend, backend, security, a11y, responsive) must go green. The **a11y** (vitest-axe + playwright-axe chromium+webkit) and **responsive** (playwright viewport chromium+webkit) jobs are the authoritative cross-engine visual/behaviour guard — if they pass, the WKWebView (Safari 17) rendering is validated. If any job fails, fix before considering SP-0 done.

- [ ] **Step 5: Report SP-0 complete**

Confirm: v4 toolchain live, iOS target 17.0, visual parity held, CI green. Note that the native device rebuild (Xcode) is deferred to the end of the rebrand programme. Next: SP-A (Foundation & rebrand spine).

---

## Self-Review

**1. Spec coverage:**
- v4 deps/plugin/PostCSS removal → Task 3. ✓
- `@import "tailwindcss"` + `@theme` token relocation (same values) → Task 4. ✓
- `tailwindcss-animate` → `tw-animate-css` → Task 3 Step 1 + the CSS `@import` in Task 4 Step 1. ✓
- `@custom-variant dark` → Task 4 Step 1. ✓
- Preserve `@layer base` (safe-area, iOS ≥16px, focus margins) → Task 4 Step 1 (verbatim). ✓
- Neutralise v4 defaults (border/ring/preflight) → audit shows pre-neutralised; Task 5 verifies + fixes only if needed. ✓
- iOS 17.0 in 4 build configs → Task 2. ✓
- Docs updated → Task 6 Step 1. ✓
- Testing/parity (build, lint, full test, screenshots, cap sync, green CI) → Tasks 1, 4, 5, 6. ✓
- Out of scope (no visual redesign, no backend, no mascot) → honoured; tokens keep amber values. ✓

**2. Placeholder scan:** No TBD/TODO. The only conditional work (Task 5 Step 3/6) is explicitly gated on an observed difference with concrete fixes given for each likely cause — not a placeholder.

**3. Consistency:** Port 5188 + `OUTDIR` env + `tmp-parity.mjs` path are consistent across Tasks 1 and 5. Token names in `@theme` match the `:root` vars and the prior `tailwind.config.js` mappings. Commit grouping (3+4 together) is called out in both tasks so no broken-build commit occurs.
