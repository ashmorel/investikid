# Accessibility (WCAG 2.2 AA) Implementation Plan (Sub-project 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring every user-facing surface to WCAG 2.2 AA and lock it with a CI gate, shared a11y primitives, surface-by-surface remediation, and a manual conformance register.

**Architecture:** Layered. Land the regression net first (eslint-plugin-jsx-a11y + vitest-axe + @axe-core/playwright in CI). Build one small set of reusable a11y primitives in `frontend/src/components/a11y/`. Then remediate by surface group, each gated by a zero-axe-violations test. Finish with manual audit + conformance register.

**Tech Stack:** React 18 + TS + Vite 6 + Tailwind 3 + Radix UI primitives + Recharts 3 + Framer Motion 12 + Vitest 3 + Playwright 1.49 + Testing Library + Lucide icons.

**Spec:** `docs/superpowers/specs/2026-05-19-accessibility-wcag22aa-design.md`

**Baselines (must stay green):** backend 328 tests; frontend 226 tests; build clean.

---

## File Structure

**Frontend create:**
- `frontend/src/components/a11y/SkipLink.tsx` — focus-visible "Skip to main content" anchor.
- `frontend/src/components/a11y/VisuallyHidden.tsx` — canonical sr-only span.
- `frontend/src/components/a11y/LiveRegion.tsx` + `useAnnounce.ts` — app-level polite live region + hook.
- `frontend/src/components/a11y/useRouteFocus.ts` — focus + announce on route change.
- `frontend/src/components/a11y/Disclosure.tsx` — accessible expand/collapse.
- `frontend/src/components/a11y/Field.tsx` — label + control + error wrapper.
- `frontend/src/components/a11y/ChartDescription.tsx` — SR summary + hidden data table for charts.
- `frontend/tests/a11y/` — vitest-axe surface tests, one per surface group.
- `frontend/tests/e2e/a11y-flow.spec.ts` — Playwright @axe-core scan.
- `frontend/docs/accessibility/conformance-2026-05.md` — WCAG 2.2 AA register.
- `frontend/docs/accessibility/authoring-guide.md` — primitives + content policy.

**Frontend modify:**
- `frontend/package.json` — add devDeps (`eslint-plugin-jsx-a11y`, `vitest-axe`, `@axe-core/playwright`).
- `frontend/eslint.config.js` — add jsx-a11y plugin + recommended rules.
- `frontend/tests/setup.ts` — register `toHaveNoViolations` matcher.
- `frontend/src/components/child/Shell.tsx` — SkipLink, main landmark id+tabIndex, useRouteFocus, reduced-motion guard.
- `frontend/src/App.tsx` — wrap with `<LiveRegion>`; ensure parent routes have a main landmark too.
- `frontend/src/components/child/simulator/PortfolioChart.tsx`, `StockChart.tsx` — wrap with role=img+aria-label, render ChartDescription.
- `frontend/src/components/child/lesson/VideoLesson.tsx` — render Disclosure transcript + captions indicator from new content_json fields.
- `frontend/src/pages/child/Signup.tsx` — convert the country + topic native selects via the existing `<Label>` (already present) and ensure `aria-required`/error wiring (use new `Field` if it simplifies).
- `frontend/src/index.css` — adjust `--ring`/`--border` and any new `--focus-ring` token for ≥3:1 against `--background`.
- `frontend/tailwind.config.js` — no theme change needed; only if a new safelist is added for the contrast fixes.
- `frontend/playwright.config.ts` — unchanged (e2e already targets `tests/e2e`).

**Backend modify:**
- `backend/app/seed/content.py` — every video-type lesson in `_MODULES` gets a non-empty `transcript` and `captions_available: true` in `content_json`.
- `backend/tests/test_video_lesson_transcripts.py` — assert every seeded video lesson has a non-empty `transcript`.

**Infra:**
- `.github/workflows/ci.yml` — add an `a11y` job (mirrors `security`) running lint + vitest-axe (already in `npm test` once setup is registered) + `@axe-core/playwright` e2e against the dev server.

---

## Task 1: jsx-a11y eslint plugin (static gate)

**Files:**
- Modify: `frontend/package.json` (devDependencies)
- Modify: `frontend/eslint.config.js`

**Context:** Flat config; existing plugins `react-hooks`, `react-refresh`. We add `eslint-plugin-jsx-a11y` at its `recommended` ruleset. Pre-existing a11y issues that surface will be fixed in later remediation tasks — for this task we install and configure the plugin, run lint to enumerate the issues, and **either** the issues are trivially zero (best case) **or** we add a single targeted `overrides` block disabling NOTHING and instead fix the small set of blocking ones inline. The plan does not allow gating via blanket disables.

- [ ] **Step 1: Install plugin**

Run: `cd frontend && npm install --save-dev eslint-plugin-jsx-a11y`
Expected: package.json updated, install succeeds.

- [ ] **Step 2: Wire into eslint.config.js**

Edit `frontend/eslint.config.js` — add the import and a new config block applying jsx-a11y/recommended:

```js
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'playwright.config.*', 'tailwind.config.js', 'vite.config.js'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'jsx-a11y': jsxA11y,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },
  {
    files: ['tests/**'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
);
```

- [ ] **Step 3: Run lint to enumerate violations**

Run: `cd frontend && npm run lint`
Expected: either passes cleanly OR lists jsx-a11y violations. If violations exist, fix each at the source — common kinds and fixes:
- `jsx-a11y/label-has-associated-control` on a label without `htmlFor`: add `htmlFor` matching the input `id`.
- `jsx-a11y/anchor-is-valid` on `<a>` used as button: convert to `<button type="button">` or add `href`.
- `jsx-a11y/click-events-have-key-events` on `<div onClick>`: make the element a `<button>` or add a `role="button"` + `tabIndex={0}` + `onKeyDown` handler converting Enter/Space to click.
- `jsx-a11y/alt-text` on `<img>`: add `alt=""` for decorative or descriptive alt for meaningful.

Make the smallest, semantically-correct change at each site; do not blanket-disable.

- [ ] **Step 4: Re-run lint until clean**

Run: `cd frontend && npm run lint`
Expected: passes with 0 errors (1 pre-existing warning in `src/components/ui/button.tsx` is acceptable — do not "fix" it as part of this task).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/eslint.config.js \
        $(git diff --name-only frontend/src)
git commit -m "feat(5): enable eslint-plugin-jsx-a11y recommended in flat config"
```
(Only stage frontend source files that you genuinely edited to satisfy lint; if none, omit that part of `git add`.)

---

## Task 2: vitest-axe + smoke test (dynamic unit gate)

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/tests/setup.ts`
- Create: `frontend/tests/a11y/smoke.test.tsx`

**Context:** `vitest-axe` exposes a `toHaveNoViolations` matcher and an `axe(node)` function. Registering it in the shared setup makes every existing component test capable of asserting a11y without each one importing it. We add a smoke test that renders a known-good component (the existing `Button`) and asserts zero violations — proves wiring works end-to-end without depending on any work later tasks will do.

- [ ] **Step 1: Install**

Run: `cd frontend && npm install --save-dev vitest-axe`
Expected: install succeeds.

- [ ] **Step 2: Register the matcher in setup**

Replace `frontend/tests/setup.ts` with:

```ts
import '@testing-library/jest-dom/vitest';
import { expect } from 'vitest';
import * as matchers from 'vitest-axe/matchers';

expect.extend(matchers);

// Make TS happy for the custom matcher across the suite.
declare module 'vitest' {
  interface Assertion<T = unknown> extends matchers.TestingLibraryMatchers<unknown, T> {
    toHaveNoViolations(): Promise<void>;
  }
}
```

If `vitest-axe/matchers` doesn't expose `TestingLibraryMatchers` type, drop the `declare module` block and rely on the runtime registration only (the matcher still works; ad-hoc `// @ts-expect-error` is acceptable on first use until typings stabilize — but try the typed form first).

- [ ] **Step 3: Write the smoke test**

Create `frontend/tests/a11y/smoke.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { Button } from '@/components/ui/button';

describe('a11y smoke', () => {
  it('Button has no violations', async () => {
    const { container } = render(<Button>OK</Button>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 4: Run**

Run: `cd frontend && npm test -- --run`
Expected: full suite green + the new smoke test passes (227 total, or whatever baseline + 1).

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tests/setup.ts frontend/tests/a11y/smoke.test.tsx
git commit -m "feat(5): register vitest-axe toHaveNoViolations matcher"
```

---

## Task 3: Playwright axe scan + CI a11y job

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tests/e2e/a11y-flow.spec.ts`
- Modify: `.github/workflows/ci.yml`

**Context:** Playwright already exists with `testDir: tests/e2e`, `baseURL: http://localhost:5173`, `webServer: npm run dev`. We add an axe spec scanning the public entry pages (no auth required — full flow can be added when auth fixtures exist in the suite, currently it doesn't). CI gets a new `a11y` job mirroring `security`: installs deps, runs `npm run lint` (already includes jsx-a11y), runs `npm test` (already includes vitest-axe), and runs the e2e a11y spec.

- [ ] **Step 1: Install**

Run: `cd frontend && npm install --save-dev @axe-core/playwright`
Expected: install succeeds.

- [ ] **Step 2: Add an `e2e:a11y` script**

In `frontend/package.json` scripts, add:
```json
    "test:e2e:a11y": "playwright test tests/e2e/a11y-flow.spec.ts"
```

- [ ] **Step 3: Write the spec**

Create `frontend/tests/e2e/a11y-flow.spec.ts`:

```ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const PAGES = [
  { path: '/login', name: 'login' },
  { path: '/signup', name: 'signup' },
  { path: '/privacy', name: 'privacy' },
  { path: '/forgot-password', name: 'forgot-password' },
];

for (const { path, name } of PAGES) {
  test(`a11y: ${name} has no serious/critical axe violations`, async ({ page }) => {
    await page.goto(path);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag22aa'])
      .analyze();
    const blocking = results.violations.filter(
      (v) => v.impact === 'serious' || v.impact === 'critical',
    );
    expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
  });
}
```

(Authenticated pages are added later when the surface-remediation tasks need them — keep this spec focused on unauth pages first so it runs without fixtures.)

- [ ] **Step 4: Run locally to confirm wiring**

Run: `cd frontend && npx playwright install chromium && npm run test:e2e:a11y`
Expected: spec runs; ANY serious/critical findings are surfaced. If findings exist, fix at the source in this task (only blocking issues on the 4 unauth pages — likely small) or defer the affected page assertion (commented `test.skip(..., 'tracked in conformance register')` with a register entry) — DO NOT silently lower severity.

- [ ] **Step 5: Add the CI a11y job**

Edit `.github/workflows/ci.yml` — append a new job after `security`:

```yaml
  a11y:
    name: A11y (lint · vitest-axe · playwright-axe)
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: invest-ed/frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: invest-ed/frontend/package-lock.json

      - run: npm ci

      - name: Lint (incl. jsx-a11y recommended)
        run: npm run lint

      - name: Unit a11y tests (vitest-axe)
        run: npm test

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      - name: E2E axe scan
        run: npm run test:e2e:a11y
```

(Lint and unit-test are already gated by the `frontend` job; the a11y job re-runs them so the a11y-suite failure modes are isolated and visible — same pattern the `security` job uses for npm audit.)

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tests/e2e/a11y-flow.spec.ts .github/workflows/ci.yml
git commit -m "feat(5): add @axe-core/playwright scan + CI a11y job"
```

---

## Task 4: SkipLink + main landmark id/tabIndex

**Files:**
- Create: `frontend/src/components/a11y/SkipLink.tsx`
- Create: `frontend/tests/a11y/SkipLink.test.tsx`
- Modify: `frontend/src/components/child/Shell.tsx` (the `<motion.main>` block at line 36–44)

**Context:** WCAG 2.4.1. The skip link must be visible only when focused, jump to the main landmark, and the main must be focusable (`tabIndex={-1}`) so the jump lands focus there.

- [ ] **Step 1: Failing test**

Create `frontend/tests/a11y/SkipLink.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { SkipLink } from '@/components/a11y/SkipLink';

describe('SkipLink', () => {
  it('renders an anchor targeting #main with the right label', () => {
    render(<><SkipLink /><main id="main" tabIndex={-1}>x</main></>);
    const link = screen.getByRole('link', { name: /skip to main content/i });
    expect(link).toHaveAttribute('href', '#main');
  });

  it('is visually-hidden until focused', async () => {
    render(<SkipLink />);
    const link = screen.getByRole('link', { name: /skip to main content/i });
    // sr-only class should hide it; focus reveals via focus: utility.
    expect(link.className).toMatch(/sr-only/);
    expect(link.className).toMatch(/focus:not-sr-only|focus-visible:not-sr-only/);
  });

  it('has no axe violations', async () => {
    const { container } = render(<><SkipLink /><main id="main" tabIndex={-1}>x</main></>);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd frontend && npm test -- --run tests/a11y/SkipLink.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

Create `frontend/src/components/a11y/SkipLink.tsx`:

```tsx
export function SkipLink() {
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-amber-800 focus:shadow focus:outline focus:outline-2 focus:outline-amber-600"
    >
      Skip to main content
    </a>
  );
}
```

- [ ] **Step 4: Wire into Shell**

In `frontend/src/components/child/Shell.tsx`:
- Add the import: `import { SkipLink } from '@/components/a11y/SkipLink';`
- Render `<SkipLink />` as the FIRST child of the outer `<div className="min-h-screen ...">` (in the success branch — the one with `TopNav`). Do NOT add it to the loading branch.
- Change `<motion.main ...>` to also have `id="main"` and `tabIndex={-1}`:

```tsx
        <motion.main
          key={location.pathname}
          id="main"
          tabIndex={-1}
          className="pb-20 md:pb-0 outline-none"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
        >
```

(`outline-none` only removes the default outline; the focus-visible ring will come from useRouteFocus styling in Task 5. Until then, the implicit focus is functional even if visually minimal.)

- [ ] **Step 5: Add a Shell-render test for the SkipLink presence**

Create `frontend/tests/a11y/Shell-skiplink.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from '@/components/child/Shell';

const ME = {
  id: 'u1', email: 'k@x.com', username: 'kid', dob: '2012-01-01',
  country_code: 'US', currency_code: 'USD', topic_path: null, is_premium: false,
  parent_email: null, created_at: '2026-04-29T00:00:00Z',
};

beforeEach(() => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(ME), { status: 200 }) as never,
  );
});

it('Shell renders SkipLink and main#main[tabindex=-1]', async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/home" element={<div>Home</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await waitFor(() => expect(screen.getByText('Home')).toBeInTheDocument());
  expect(screen.getByRole('link', { name: /skip to main content/i })).toHaveAttribute('href', '#main');
  const main = document.querySelector('main#main')!;
  expect(main).toBeTruthy();
  expect(main).toHaveAttribute('tabindex', '-1');
});
```

- [ ] **Step 6: Run**

Run: `cd frontend && npm test -- --run tests/a11y/`
Expected: all a11y tests green (smoke + SkipLink + Shell-skiplink).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/a11y/SkipLink.tsx frontend/src/components/child/Shell.tsx frontend/tests/a11y/SkipLink.test.tsx frontend/tests/a11y/Shell-skiplink.test.tsx
git commit -m "feat(5): SkipLink + main landmark for keyboard users"
```

---

## Task 5: useRouteFocus + LiveRegion + useAnnounce

**Files:**
- Create: `frontend/src/components/a11y/useRouteFocus.ts`
- Create: `frontend/src/components/a11y/LiveRegion.tsx`
- Create: `frontend/src/components/a11y/useAnnounce.ts`
- Modify: `frontend/src/App.tsx` (wrap with `<LiveRegion>`)
- Modify: `frontend/src/components/child/Shell.tsx` (call `useRouteFocus`)
- Create: `frontend/tests/a11y/useRouteFocus.test.tsx`
- Create: `frontend/tests/a11y/LiveRegion.test.tsx`

**Context:** WCAG 2.4.3 / 4.1.3. On every Router location change focus is moved to `#main` and the new page title (derived from `document.title` or a passed-in label) is announced via a polite live region. `useAnnounce` exposes a setter consumers can call for non-route async announcements.

- [ ] **Step 1: Failing tests**

Create `frontend/tests/a11y/LiveRegion.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { LiveRegion } from '@/components/a11y/LiveRegion';
import { useAnnounce } from '@/components/a11y/useAnnounce';

function Caller() {
  const announce = useAnnounce();
  return <button onClick={() => announce('Saved')}>save</button>;
}

describe('LiveRegion', () => {
  it('exposes a polite live region', () => {
    render(<LiveRegion><Caller /></LiveRegion>);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
  });

  it('announces messages from useAnnounce', () => {
    render(<LiveRegion><Caller /></LiveRegion>);
    act(() => { screen.getByText('save').click(); });
    expect(screen.getByRole('status')).toHaveTextContent('Saved');
  });
});
```

Create `frontend/tests/a11y/useRouteFocus.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useRouteFocus } from '@/components/a11y/useRouteFocus';
import { LiveRegion } from '@/components/a11y/LiveRegion';

function Layout() {
  useRouteFocus();
  return (
    <>
      <main id="main" tabIndex={-1}>main</main>
      <Nav />
    </>
  );
}

function Nav() {
  const navigate = useNavigate();
  return <button onClick={() => navigate('/b')}>go b</button>;
}

it('moves focus to #main and announces on route change', async () => {
  document.title = 'Page B — Invest-Ed';
  render(
    <LiveRegion>
      <MemoryRouter initialEntries={['/a']}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/a" element={<div>a</div>} />
            <Route path="/b" element={<div>b</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </LiveRegion>,
  );
  await act(async () => { screen.getByText('go b').click(); });
  expect(document.activeElement?.id).toBe('main');
  expect(screen.getByRole('status')).toHaveTextContent(/Page B/);
});
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd frontend && npm test -- --run tests/a11y/LiveRegion.test.tsx tests/a11y/useRouteFocus.test.tsx`
Expected: FAIL (modules not found).

- [ ] **Step 3: Implement LiveRegion + useAnnounce**

Create `frontend/src/components/a11y/LiveRegion.tsx`:

```tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

const AnnounceContext = createContext<(msg: string) => void>(() => {});

export function LiveRegion({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState('');
  const announce = useCallback((next: string) => {
    // Force change-detection even if same message is announced twice.
    setMsg('');
    setTimeout(() => setMsg(next), 0);
  }, []);
  return (
    <AnnounceContext.Provider value={announce}>
      {children}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {msg}
      </div>
    </AnnounceContext.Provider>
  );
}

export const _AnnounceContext = AnnounceContext;
```

Create `frontend/src/components/a11y/useAnnounce.ts`:

```ts
import { useContext } from 'react';
import { _AnnounceContext } from './LiveRegion';

export function useAnnounce() {
  return useContext(_AnnounceContext);
}
```

- [ ] **Step 4: Implement useRouteFocus**

Create `frontend/src/components/a11y/useRouteFocus.ts`:

```ts
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useAnnounce } from './useAnnounce';

export function useRouteFocus() {
  const { pathname } = useLocation();
  const announce = useAnnounce();
  const firstRender = useRef(true);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const main = document.getElementById('main');
    if (main) {
      main.focus({ preventScroll: false });
    }
    // document.title is set by the page; fallback to 'Page updated'.
    const title = document.title || 'Page updated';
    announce(title);
  }, [pathname, announce]);
}
```

- [ ] **Step 5: Wire**

In `frontend/src/App.tsx` wrap the `<Routes>` (and any sibling like `<Toaster />`) with `<LiveRegion>`:

```tsx
import { LiveRegion } from '@/components/a11y/LiveRegion';
// ...
  return (
    <LiveRegion>
      <Routes>{/* ...unchanged... */}</Routes>
      <Toaster />
    </LiveRegion>
  );
```

In `frontend/src/components/child/Shell.tsx`, add `import { useRouteFocus } from '@/components/a11y/useRouteFocus';` and call `useRouteFocus();` at the top of the `Shell` component, right after `const location = useLocation();`.

- [ ] **Step 6: Run**

Run: `cd frontend && npm test -- --run`
Expected: full suite green (228 + 2 new = 230).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/a11y/useRouteFocus.ts \
        frontend/src/components/a11y/LiveRegion.tsx \
        frontend/src/components/a11y/useAnnounce.ts \
        frontend/src/App.tsx \
        frontend/src/components/child/Shell.tsx \
        frontend/tests/a11y/useRouteFocus.test.tsx \
        frontend/tests/a11y/LiveRegion.test.tsx
git commit -m "feat(5): useRouteFocus + LiveRegion/useAnnounce primitives"
```

---

## Task 6: VisuallyHidden + Disclosure + Field

**Files:**
- Create: `frontend/src/components/a11y/VisuallyHidden.tsx`
- Create: `frontend/src/components/a11y/Disclosure.tsx`
- Create: `frontend/src/components/a11y/Field.tsx`
- Create: `frontend/tests/a11y/Disclosure.test.tsx`
- Create: `frontend/tests/a11y/Field.test.tsx`

**Context:** Three small primitives reused later. `Disclosure` is a button + region pair with `aria-expanded`/`aria-controls`. `Field` standardises label + control + error wiring.

- [ ] **Step 1: Failing tests**

Create `frontend/tests/a11y/Disclosure.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { Disclosure } from '@/components/a11y/Disclosure';

describe('Disclosure', () => {
  it('is collapsed by default and toggles on click', async () => {
    const u = userEvent.setup();
    render(<Disclosure label="Transcript">Hello world</Disclosure>);
    const btn = screen.getByRole('button', { name: /transcript/i });
    expect(btn).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('Hello world')).not.toBeVisible();
    await u.click(btn);
    expect(btn).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('Hello world')).toBeVisible();
  });

  it('button controls the panel by aria-controls/id', () => {
    render(<Disclosure label="X">body</Disclosure>);
    const btn = screen.getByRole('button');
    const controlsId = btn.getAttribute('aria-controls')!;
    expect(document.getElementById(controlsId)).toBeTruthy();
  });

  it('has no axe violations open or closed', async () => {
    const u = userEvent.setup();
    const { container } = render(<Disclosure label="X">body</Disclosure>);
    expect(await axe(container)).toHaveNoViolations();
    await u.click(screen.getByRole('button'));
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

Create `frontend/tests/a11y/Field.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { Field } from '@/components/a11y/Field';

describe('Field', () => {
  it('associates label, control, and error', () => {
    render(
      <Field id="email" label="Email" error="Required">
        <input id="email" />
      </Field>,
    );
    const input = screen.getByLabelText('Email');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    const describedBy = input.getAttribute('aria-describedby')!;
    expect(document.getElementById(describedBy)).toHaveTextContent('Required');
  });

  it('renders without error and is axe-clean', async () => {
    const { container } = render(
      <Field id="name" label="Name">
        <input id="name" />
      </Field>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd frontend && npm test -- --run tests/a11y/Disclosure.test.tsx tests/a11y/Field.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement VisuallyHidden**

Create `frontend/src/components/a11y/VisuallyHidden.tsx`:

```tsx
import type { HTMLAttributes, ReactNode } from 'react';

export function VisuallyHidden({ children, ...rest }: HTMLAttributes<HTMLSpanElement> & { children: ReactNode }) {
  return <span {...rest} className={`sr-only ${rest.className ?? ''}`}>{children}</span>;
}
```

- [ ] **Step 4: Implement Disclosure**

Create `frontend/src/components/a11y/Disclosure.tsx`:

```tsx
import { useId, useState, type ReactNode } from 'react';

type Props = { label: string; defaultOpen?: boolean; children: ReactNode };

export function Disclosure({ label, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((o) => !o)}
        className="text-sm font-semibold text-amber-700 underline"
      >
        {label}
      </button>
      <div id={panelId} hidden={!open} className="mt-2 text-sm text-gray-700">
        {children}
      </div>
    </div>
  );
}
```

(`hidden` attribute is the simplest way to make the panel inaccessible to AT when closed and is correctly reported by `toBeVisible` matchers.)

- [ ] **Step 5: Implement Field**

Create `frontend/src/components/a11y/Field.tsx`:

```tsx
import { cloneElement, useId, type ReactElement } from 'react';
import { Label } from '@/components/ui/label';

type Props = {
  id: string;
  label: string;
  error?: string | null;
  hint?: string;
  children: ReactElement;
};

export function Field({ id, label, error, hint, children }: Props) {
  const errorId = useId();
  const hintId = useId();
  const describedBy =
    [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(' ') || undefined;

  const control = cloneElement(children, {
    id,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy,
  });

  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {control}
      {hint && <p id={hintId} className="text-xs text-muted-foreground">{hint}</p>}
      {error && <p id={errorId} role="alert" className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 6: Run**

Run: `cd frontend && npm test -- --run tests/a11y/`
Expected: green.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/a11y/VisuallyHidden.tsx \
        frontend/src/components/a11y/Disclosure.tsx \
        frontend/src/components/a11y/Field.tsx \
        frontend/tests/a11y/Disclosure.test.tsx \
        frontend/tests/a11y/Field.test.tsx
git commit -m "feat(5): VisuallyHidden + Disclosure + Field primitives"
```

---

## Task 7: ChartDescription + wire into PortfolioChart + StockChart

**Files:**
- Create: `frontend/src/components/a11y/ChartDescription.tsx`
- Modify: `frontend/src/components/child/simulator/PortfolioChart.tsx`
- Modify: `frontend/src/components/child/simulator/StockChart.tsx`
- Create: `frontend/tests/a11y/ChartDescription.test.tsx`
- Create: `frontend/tests/a11y/PortfolioChart.a11y.test.tsx`

**Context:** WCAG 1.1.1. Each chart wraps its Recharts SVG with `role="img"` + `aria-label` carrying a one-sentence summary, and renders a `VisuallyHidden` `<table>` of the data points beside it. Underlying data is already in props (`history` for portfolio, `points` for stock).

- [ ] **Step 1: Failing test**

Create `frontend/tests/a11y/ChartDescription.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { ChartDescription } from '@/components/a11y/ChartDescription';

describe('ChartDescription', () => {
  it('renders summary and a hidden data table', () => {
    render(
      <ChartDescription
        summary="Portfolio rose from £100 to £120 over 4 days."
        columns={['Date', 'Value']}
        rows={[['Mon', '100'], ['Tue', '105'], ['Wed', '115'], ['Thu', '120']]}
      />,
    );
    expect(screen.getByText(/Portfolio rose/)).toBeInTheDocument();
    const table = screen.getByRole('table');
    expect(table).toBeInTheDocument();
    // 1 header row + 4 data rows
    expect(screen.getAllByRole('row')).toHaveLength(5);
  });

  it('is axe-clean', async () => {
    const { container } = render(
      <ChartDescription summary="x" columns={['A']} rows={[['1']]} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd frontend && npm test -- --run tests/a11y/ChartDescription.test.tsx`
Expected: FAIL.

- [ ] **Step 3: Implement**

Create `frontend/src/components/a11y/ChartDescription.tsx`:

```tsx
import { VisuallyHidden } from './VisuallyHidden';

type Props = {
  summary: string;
  columns: string[];
  rows: (string | number)[][];
};

export function ChartDescription({ summary, columns, rows }: Props) {
  return (
    <VisuallyHidden>
      <p>{summary}</p>
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c} scope="col">{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>{r.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </VisuallyHidden>
  );
}
```

- [ ] **Step 4: Wire PortfolioChart**

In `frontend/src/components/child/simulator/PortfolioChart.tsx`, after the existing imports add:
```ts
import { ChartDescription } from '@/components/a11y/ChartDescription';
```
Replace the return block with one that wraps the Recharts container in `role="img"` and includes the description. Compute summary from `history`:

```tsx
  if (history.length < 2) return null;

  const start = history[0].value;
  const end = history[history.length - 1].value;
  const delta = end - start;
  const pct = start > 0 ? (delta / start) * 100 : 0;
  const dir = delta >= 0 ? 'rose' : 'fell';
  const summary = `Portfolio ${dir} from ${start.toFixed(2)} to ${end.toFixed(2)} (${pct.toFixed(1)}%) across ${history.length} points.`;

  return (
    <div
      className="mt-4 rounded-2xl border-2 border-amber-200 bg-white p-4"
      role="img"
      aria-label={summary}
    >
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Portfolio Value</h3>
      <ResponsiveContainer width="100%" height={200}>
        {/* ...existing AreaChart unchanged... */}
      </ResponsiveContainer>
      <ChartDescription
        summary={summary}
        columns={['Date', 'Value']}
        rows={history.map((p) => [String(p.date), p.value.toFixed(2)])}
      />
    </div>
  );
```

(Keep the AreaChart contents exactly as currently written; only wrap the outer container and add the ChartDescription block.)

- [ ] **Step 5: Wire StockChart**

In `frontend/src/components/child/simulator/StockChart.tsx`, do the equivalent: compute a summary from `points` (already calculated as `startPrice`/`endPrice`/`change`/`changePct`), add `role="img"` and `aria-label` to the outer card div, and render `<ChartDescription>` with `columns={['Date', 'Close']}` and rows from `points`. Read `points`/`hasData` already in scope. Add the import at the top.

- [ ] **Step 6: A11y assertion test**

Create `frontend/tests/a11y/PortfolioChart.a11y.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { PortfolioChart } from '@/components/child/simulator/PortfolioChart';

describe('PortfolioChart a11y', () => {
  const history = [
    { date: '2026-05-01', value: 100 },
    { date: '2026-05-02', value: 110 },
    { date: '2026-05-03', value: 120 },
  ];

  it('container is role=img with summary label', () => {
    render(<PortfolioChart history={history as never} />);
    const region = screen.getByRole('img', { name: /portfolio/i });
    expect(region).toBeInTheDocument();
  });

  it('exposes a data table via ChartDescription', () => {
    render(<PortfolioChart history={history as never} />);
    expect(screen.getByRole('table')).toBeInTheDocument();
  });

  it('is axe-clean', async () => {
    const { container } = render(<PortfolioChart history={history as never} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 7: Run**

Run: `cd frontend && npm test -- --run`
Expected: full suite green (+3 new chart tests).

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/a11y/ChartDescription.tsx \
        frontend/src/components/child/simulator/PortfolioChart.tsx \
        frontend/src/components/child/simulator/StockChart.tsx \
        frontend/tests/a11y/ChartDescription.test.tsx \
        frontend/tests/a11y/PortfolioChart.a11y.test.tsx
git commit -m "feat(5): chart text alternatives via ChartDescription"
```

---

## Task 8: Backend video lesson transcripts (seed + assertion)

**Files:**
- Modify: `backend/app/seed/content.py` (every `type: video` lesson's `content_json`)
- Create: `backend/tests/test_video_lesson_transcripts.py`

**Context:** No DB migration — `Lesson.content_json` is free-form JSON. The backend `LessonOut` schema passes it through unchanged. Every seeded video lesson must gain a non-empty `transcript: str` and `captions_available: True` so the frontend can render the Disclosure deterministically. The seed upsert (per sub-project 4b's update) refreshes existing rows' `icon`/`is_premium` but NOT `content_json` — so the assertion test runs against the in-memory `_MODULES` data structure, not against a DB row.

- [ ] **Step 1: Failing test**

Create `backend/tests/test_video_lesson_transcripts.py`:

```python
from app.seed.content import _MODULES


def test_every_seeded_video_lesson_has_non_empty_transcript_and_captions_flag():
    video_lessons = [
        lesson
        for module in _MODULES
        for lesson in module["lessons"]
        if lesson["type"] == "video"
    ]
    assert video_lessons, "expected at least one seeded video lesson in _MODULES"
    for lesson in video_lessons:
        content = lesson["content_json"]
        assert content.get("transcript"), (
            f"video lesson {content.get('caption') or content!r} missing non-empty transcript"
        )
        assert content.get("captions_available") is True, (
            f"video lesson {content.get('caption') or content!r} missing captions_available=True"
        )
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd backend && python -m pytest tests/test_video_lesson_transcripts.py -q`
Expected: FAIL — every seeded video lesson missing the new fields.

- [ ] **Step 3: Add transcripts to seed**

In `backend/app/seed/content.py`, iterate the `_MODULES` list and for every lesson with `"type": "video"` add a `"transcript": "<plain-text summary of the video that covers the same teaching points>"` and `"captions_available": True` inside its `content_json`. Transcript content must:
- Be ≥ 80 characters of meaningful text covering the same learning content as the video.
- Use kid-friendly language consistent with the lesson's other content fields.
- Not assert any specific real-world financial advice (consistent with 4a moderation rules).

If there are no video lessons in the seed today (verify with `grep -n '"type": "video"' backend/app/seed/content.py`), add the assertion-test note in the conformance register's residual items, change Step 1's test to skip rather than fail, and proceed — but DO NOT silently drop the test; the register entry must say "no video lessons currently seeded; transcript policy enforced when added".

(In the codebase as audited, video lessons are referenced in fixtures but check whether `_MODULES` actually contains any video entries before authoring transcripts.)

- [ ] **Step 4: Run, confirm pass**

Run: `cd backend && python -m pytest tests/test_video_lesson_transcripts.py -q`
Expected: PASS.

- [ ] **Step 5: Full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: 329 passed (328 baseline + 1 new), 0 failed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/seed/content.py backend/tests/test_video_lesson_transcripts.py
git commit -m "feat(5): seed video lesson transcripts + captions flag"
```

---

## Task 9: VideoLesson renders Disclosure transcript + captions indicator

**Files:**
- Modify: `frontend/src/components/child/lesson/VideoLesson.tsx`
- Modify: `frontend/tests/unit/child-VideoLesson.test.tsx`

**Context:** The component already accepts `contentJson` of type `{ youtube_id?; caption? }`. Extend the inline prop type to include `transcript?` and `captions_available?`, render the `Disclosure` for transcript when present, and show a small "Captions available" / "No captions" indicator from the flag. Keep all existing behaviour (watched checkbox, fallback when youtube_id missing, etc.).

- [ ] **Step 1: Update the component**

In `frontend/src/components/child/lesson/VideoLesson.tsx`:

- Add import: `import { Disclosure } from '@/components/a11y/Disclosure';`
- Extend `Props.contentJson` to:
  ```ts
  contentJson: { youtube_id?: string; caption?: string; transcript?: string; captions_available?: boolean };
  ```
- In the JSX, immediately AFTER the existing `{contentJson.caption && ...}` block, render:
  ```tsx
        <p className="text-xs text-muted-foreground">
          {contentJson.captions_available ? 'Captions available' : 'No captions'}
        </p>
        {contentJson.transcript && (
          <Disclosure label="Show transcript">
            {contentJson.transcript}
          </Disclosure>
        )}
  ```

- [ ] **Step 2: Update tests**

Extend `frontend/tests/unit/child-VideoLesson.test.tsx` with two new cases (keep existing tests intact):

```tsx
import { axe } from 'vitest-axe';

it('renders captions indicator and a disclosure for transcript', async () => {
  const u = userEvent.setup();
  render(
    <VideoLesson
      contentJson={{ youtube_id: 'abc', captions_available: true, transcript: 'Hello world transcript content.' }}
      onComplete={() => {}}
    />,
  );
  expect(screen.getByText(/Captions available/)).toBeInTheDocument();
  const trigger = screen.getByRole('button', { name: /show transcript/i });
  expect(trigger).toHaveAttribute('aria-expanded', 'false');
  await u.click(trigger);
  expect(screen.getByText('Hello world transcript content.')).toBeVisible();
});

it('shows "No captions" when flag is false and omits transcript when missing', () => {
  render(<VideoLesson contentJson={{ youtube_id: 'abc', captions_available: false }} onComplete={() => {}} />);
  expect(screen.getByText(/No captions/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /show transcript/i })).not.toBeInTheDocument();
});

it('has no axe violations', async () => {
  const { container } = render(
    <VideoLesson
      contentJson={{ youtube_id: 'abc', captions_available: true, transcript: 't' }}
      onComplete={() => {}}
    />,
  );
  expect(await axe(container)).toHaveNoViolations();
});
```

Add the import `import userEvent from '@testing-library/user-event';` if not already present.

- [ ] **Step 3: Run**

Run: `cd frontend && npm test -- --run tests/unit/child-VideoLesson.test.tsx`
Expected: green (existing 3 + new 3 = 6).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/child/lesson/VideoLesson.tsx frontend/tests/unit/child-VideoLesson.test.tsx
git commit -m "feat(5): VideoLesson shows transcript Disclosure + captions indicator"
```

---

## Task 10: Surface-by-surface remediation (axe-driven loop)

**Files (per surface group):**
- Create: `frontend/tests/a11y/<group>.a11y.test.tsx` — renders the surface and asserts `toHaveNoViolations`.
- Modify: the surface's source file(s) only as required to satisfy the gate.

**Context:** With the gate installed (jsx-a11y + vitest-axe) and primitives ready, this task drives remediation by writing a zero-violations test per surface group, fixing what fails until each test is green, then committing per group. The remediation IS the test loop — there is no useful "implement this code" instruction in advance, because the exact set of fixes depends on what axe + jsx-a11y report against the live components. The plan specifies the surface groups, the acceptance rule, the allowed fix patterns, and what to commit per group.

**Acceptance per group:** `expect(await axe(container)).toHaveNoViolations()` passes for the group's representative render(s); `npm run lint` stays clean; existing component behavior tests remain green; targeted RTL assertions added for any non-trivial semantic fix (named role, accessible name, focus order).

**Allowed fix patterns (no others):**
- Replace `<div onClick>` with `<button type="button">` (or add `role="button" tabIndex={0}` + `onKeyDown` Enter/Space) — match Radix patterns already in the codebase.
- Add `htmlFor`/`id` to label/control pairs. For native `<select>` that lacks one, wrap with the new `Field` primitive when it simplifies, otherwise add the missing `<Label htmlFor>` pair.
- Add `aria-label` / `aria-labelledby` to icon-only buttons (existing pattern: see `ProfileMenu` trigger uses `aria-label`).
- For inline SVG illustrations rendered for decoration, add `aria-hidden="true"`. For meaningful inline SVG, wrap with `role="img"` + `aria-label`.
- Replace ad-hoc `sr-only` spans with the new `<VisuallyHidden>`.
- Color contrast: adjust the offending Tailwind utility class to use a token meeting ≥4.5:1 against its background (e.g. `text-gray-400` → `text-gray-600`). Do NOT silently change brand color; if a brand color fails, add a Section-3-style contrast register row instead and pick the closest passing shade.
- Focus-not-obscured (2.4.11): add `scroll-margin-top` to focusable elements behind sticky `TopNav`/`BottomTabBar`.
- Target size (2.5.8): bump touch targets in `BottomTabBar` (currently `h-16` container, icon `h-5 w-5`) so the tap target meets ≥24×24 CSS px (✓ already) AND visible icon plus label render together; if a smaller interactive element exists (e.g. lesson row icons used as buttons) ensure the underlying button is ≥24×24.

**Surface groups (each is a checkbox + its own commit):**

- [ ] **Group 1: Auth & entry** — Signup, Login, PendingConsent, ConsentVerify, VerifyEmail, ForgotPassword, ResetPassword, Privacy, ParentLogin, ParentAuthCallback.
  - New test file: `frontend/tests/a11y/auth-entry.a11y.test.tsx` — renders each page (use MemoryRouter; mock `fetch` for `me`/data fetches as the existing `child-Signup.test.tsx` does), asserts `toHaveNoViolations`.
  - Likely fix: the Signup country + topic native `<select>`s already have `<Label htmlFor>` correctly per audit; verify and fix any remaining axe finding (e.g. `aria-required` on required selects).
  - Commit: `git commit -m "fix(5): a11y remediation — auth & entry surfaces"`.

- [ ] **Group 2: Child core** — Home, Lessons, Module, Lesson, Stats.
  - New test file: `frontend/tests/a11y/child-core.a11y.test.tsx`.
  - Likely fix: heading order; `<button>`-vs-`<div>` for card actions; `aria-current="page"` on active nav (already on `NavLink` via Radix? if not, set `aria-current` from `isActive`).
  - Commit: `git commit -m "fix(5): a11y remediation — child core pages"`.

- [ ] **Group 3: Lesson renderers** — Card, Video, Scenario, Quiz, Practice.
  - New test file: `frontend/tests/a11y/lesson-renderers.a11y.test.tsx`.
  - Existing strengths (audit): QuizLesson is `role="radiogroup"` keyboard-operable; VideoLesson already updated in Task 9. Likely fix: the practice "Challenge"/"Warm-up"/"Practice — no XP" badges' purple/blue contrast → adjust to `bg-purple-100 text-purple-900` (was `text-purple-800`) etc. if axe contrast fails.
  - Commit: `git commit -m "fix(5): a11y remediation — lesson renderers"`.

- [ ] **Group 4: Simulator** — Simulator, TradeForm, HoldingsTable, MarketSearchBar, MarketNews, StockNews, the news widgets.
  - New test file: `frontend/tests/a11y/simulator.a11y.test.tsx`.
  - Likely fix: HoldingsTable → proper `<table>` semantics with `<th scope="col">`; MarketSearchBar → ARIA combobox pattern (input with `role="combobox" aria-expanded aria-controls`, list with `role="listbox"`, items with `role="option"`).
  - Commit: `git commit -m "fix(5): a11y remediation — simulator surfaces"`.

- [ ] **Group 5: Parent** — ParentDashboard (and its child cards if any axe finding surfaces there too).
  - New test file: `frontend/tests/a11y/parent.a11y.test.tsx`.
  - Commit: `git commit -m "fix(5): a11y remediation — parent dashboard"`.

- [ ] **For each group above, follow this sub-process:**
  1. Write the per-group a11y test renderer (use the existing `child-<Surface>.test.tsx` files as the render-pattern template for routing/QueryClient/fetch mocking).
  2. Run `cd frontend && npm test -- --run tests/a11y/<group>.a11y.test.tsx` — observe failures.
  3. Fix at the source using only the allowed patterns above. Run lint after each fix (`npm run lint`).
  4. Re-run until green.
  5. Run the full suite: `cd frontend && npm test -- --run` → all green.
  6. Commit per the group's message above.

If a finding cannot be fixed without a brand/scope change (e.g. a third-party YouTube colour), STOP that group, add a register entry (Task 12), and use `test.skip` with an explicit reason citing the register row — DO NOT silently lower severity in code.

---

## Task 11: Cross-cutting — contrast tokens, reduced-motion, WCAG 2.2-new

**Files:**
- Modify: `frontend/src/index.css` (CSS vars / focus ring)
- Modify: `frontend/src/components/child/Shell.tsx` (Framer Motion `prefers-reduced-motion`)
- Modify: `frontend/src/components/child/BottomTabBar.tsx` and any other sticky element (focus-not-obscured)
- Create: `frontend/tests/a11y/reduced-motion.test.tsx`

**Context:** Three WCAG criteria not handled by the per-surface pass above.

- [ ] **Step 1: Contrast/focus-ring token review**

Open `frontend/src/index.css`. Verify (in browser DevTools or via WebAIM contrast checker):
- `--foreground` (HSL 220 9% 12% ≈ #1B1F22) on `--background` (HSL 48 100% 96% ≈ #FFF8E1) → expect ≥7:1 (passes AAA).
- `--ring` (HSL 38 92% 50% ≈ amber-500 #F59E0B) on `--background` → expect ≥3:1 for non-text UI; if it fails, swap `--ring` to a darker shade (e.g. `38 92% 35%`) and confirm the button focus-visible ring remains visually identifiable.
- Any per-component class flagged by axe in Task 10 contrast checks (already addressed surface-by-surface; this step is the canonical token sweep).

If a token change is needed, make the smallest swap (one HSL number) and run `npm test -- --run` to confirm nothing visually-coupled breaks. Snapshot-style tests are not used; behavioural tests should survive a color shift.

- [ ] **Step 2: `prefers-reduced-motion` for route transitions**

In `frontend/src/components/child/Shell.tsx`, gate the Framer Motion `<motion.main>` animation properties so they're skipped when the user prefers reduced motion. Add a hook (Framer Motion already exposes `useReducedMotion`):

```tsx
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
// ...
  const prefersReducedMotion = useReducedMotion();
// ...
        <motion.main
          key={location.pathname}
          id="main"
          tabIndex={-1}
          className="pb-20 md:pb-0 outline-none"
          initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
          animate={prefersReducedMotion ? undefined : { opacity: 1, y: 0 }}
          exit={prefersReducedMotion ? undefined : { opacity: 0, y: -8 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.15 }}
        >
```

- [ ] **Step 3: Reduced-motion test**

Create `frontend/tests/a11y/reduced-motion.test.tsx`:

```tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shell } from '@/components/child/Shell';

const ME = {
  id: 'u1', email: 'k@x.com', username: 'kid', dob: '2012-01-01',
  country_code: 'US', currency_code: 'USD', topic_path: null, is_premium: false,
  parent_email: null, created_at: '2026-04-29T00:00:00Z',
};

beforeEach(() => {
  // Force prefers-reduced-motion: reduce
  window.matchMedia = vi.fn().mockImplementation((q) => ({
    matches: q.includes('reduce'),
    media: q,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(ME), { status: 200 }) as never,
  );
});

it('Shell honours prefers-reduced-motion (no transform/opacity animation on main)', async () => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { container } = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/home']}>
        <Routes>
          <Route element={<Shell />}>
            <Route path="/home" element={<div>Home</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await waitFor(() => expect(container.textContent).toContain('Home'));
  // When reduced-motion is set, framer-motion does not apply a transform animation.
  const main = container.querySelector('main#main')! as HTMLElement;
  // The inline style should not contain a translate transform.
  expect(main.style.transform || '').not.toMatch(/translateY|matrix/);
});
```

(This is a behavioural check; if jsdom + framer-motion makes it flaky, replace with a unit check on the value `useReducedMotion` returns by mocking the hook directly — keep the assertion that the animation is skipped, not the implementation.)

- [ ] **Step 4: WCAG 2.2-new — focus-not-obscured (2.4.11)**

Add a small global utility for elements that may be reached by keyboard while a sticky element overlaps them. The simplest, lowest-risk fix: in `frontend/src/index.css` add to `@layer base`:

```css
  :focus-visible { scroll-margin-top: 4.5rem; scroll-margin-bottom: 5rem; }
```

(The TopNav is `h-14` ≈ 3.5rem, BottomTabBar is `h-16` ≈ 4rem; the margins give a one-line buffer.)

- [ ] **Step 5: WCAG 2.2-new — target size (2.5.8)**

Inspect `BottomTabBar.tsx`: tap targets are full-width via `flex justify-around` over `h-16`. Each `NavLink` is `flex flex-col px-3 py-1` → effective ≥48px tall × column-width wide → meets 2.5.8 (24×24 minimum, 48×48 recommended) ✓. Re-confirm in a test:

Add to `frontend/tests/a11y/BottomTabBar.target-size.test.tsx`:

```tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { BottomTabBar } from '@/components/child/BottomTabBar';

it('every tab target is at least 44px square (computed-style sanity)', () => {
  render(<MemoryRouter><BottomTabBar /></MemoryRouter>);
  for (const link of screen.getAllByRole('link')) {
    // jsdom doesn't compute real layout; assert the container chain implies adequate size.
    const nav = link.closest('nav')!;
    expect(nav.className).toMatch(/\bh-16\b/);
  }
});
```

(If a true layout assertion is needed, defer to the Playwright axe scan — jsdom isn't a layout engine.)

- [ ] **Step 6: Run full suite + lint**

Run: `cd frontend && npm run lint && npm test -- --run`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/index.css \
        frontend/src/components/child/Shell.tsx \
        frontend/src/components/child/BottomTabBar.tsx \
        frontend/tests/a11y/reduced-motion.test.tsx \
        frontend/tests/a11y/BottomTabBar.target-size.test.tsx
git commit -m "fix(5): cross-cutting — reduced-motion + focus-not-obscured + tokens"
```

---

## Task 12: Docs — conformance register + authoring guide

**Files:**
- Create: `frontend/docs/accessibility/conformance-2026-05.md`
- Create: `frontend/docs/accessibility/authoring-guide.md`

**Context:** The conformance register is the manual-audit half of the AA claim. It mirrors `invest-ed/docs/security/audit-2026-05.md` (the security register). The authoring guide is the short doc developers consult to use the new primitives.

- [ ] **Step 1: Manual keyboard pass**

Manually drive the app keyboard-only against each surface group from Task 10. Record per surface in the register: reachable ✓/✗, operable ✓/✗, focus visible ✓/✗, logical order ✓/✗, no traps ✓/✗, skip-link works ✓/✗.

- [ ] **Step 2: Manual VoiceOver pass (macOS Safari)**

Same surface groups. Record names/roles/states correct, live-region announcements heard, transcript/chart-table consumable, errors clear. Note any source-dependent residuals (e.g. YouTube auto-caption quality on a specific source video).

- [ ] **Step 3: Write the conformance register**

Create `frontend/docs/accessibility/conformance-2026-05.md` with these sections (use the security register as the structural template):

1. Scope and AA target.
2. Tooling summary (jsx-a11y, vitest-axe, @axe-core/playwright, CI a11y job — pointers to the configs).
3. Manual audit method (keyboard, VoiceOver/Safari, 200% zoom, 320px reflow).
4. WCAG 2.2 AA criterion × surface-group matrix: Pass / Fail / N-A with one-line notes for non-trivial entries. Each Fail links to the commit/test that closed it.
5. Residual / source-dependent items (e.g. third-party YouTube caption authenticity, any moderate/minor axe finding logged here rather than auto-failed).
6. How the gate enforces it ongoing (lint, vitest-axe, Playwright).

- [ ] **Step 4: Write the authoring guide**

Create `frontend/docs/accessibility/authoring-guide.md`:

1. The primitives (`SkipLink`, `useRouteFocus`, `LiveRegion`/`useAnnounce`, `VisuallyHidden`, `Disclosure`, `Field`, `ChartDescription`) — one-paragraph usage each with a code snippet.
2. The video-lesson content policy: "Only captioned YouTube sources may be used. Every video lesson MUST ship a non-empty `transcript` and set `captions_available: true`. The `backend/tests/test_video_lesson_transcripts.py` test enforces this on seed data."
3. The DO-NOT-DISABLE rule: never silence jsx-a11y or axe via blanket disables; fix at the source or add a residual register row with a tracking link.
4. Pointer to the conformance register.

- [ ] **Step 5: Commit**

```bash
git add frontend/docs/accessibility/conformance-2026-05.md frontend/docs/accessibility/authoring-guide.md
git commit -m "docs(5): WCAG 2.2 AA conformance register + a11y authoring guide"
```

---

## Task 13: Full regression + close-out

**Files:**
- Modify: `docs/superpowers/specs/2026-05-19-accessibility-wcag22aa-design.md` (mark Delivered)

- [ ] **Step 1: Full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: 329 passed (328 baseline + 1 new), 0 failed.

- [ ] **Step 2: Full frontend suite + lint + build**

Run: `cd frontend && npm run lint && npm test -- --run && npm run build`
Expected: lint clean (only the pre-existing button.tsx warning), all tests green, build succeeds.

- [ ] **Step 3: E2E a11y scan**

Run: `cd frontend && npm run test:e2e:a11y`
Expected: green (the unauth pages — all axe serious/critical clean; authenticated pages remain out of e2e scope per Task 3).

- [ ] **Step 4: Spec-alignment checklist**

Verify each spec section maps to a committed task:
- §1 Tooling & CI gate → Tasks 1, 2, 3 ✔
- §2 Primitives → Tasks 4, 5, 6, 7 ✔
- §3 Remediation surfaces + manual audit → Task 10 (groups) + Task 11 (cross-cutting) + Task 12 (manual audit) ✔
- §4 Content model + chart a11y + tests + register → Tasks 7, 8, 9, 12 ✔

If a gap is found, fix before close-out.

- [ ] **Step 5: Mark spec delivered**

In `docs/superpowers/specs/2026-05-19-accessibility-wcag22aa-design.md`, change the Status line from
`**Status:** Approved (brainstorming) — 2026-05-19`
to
`**Status:** Delivered — 2026-05-19 (sub-project 5)`.

- [ ] **Step 6: Commit close-out**

```bash
git add docs/superpowers/specs/2026-05-19-accessibility-wcag22aa-design.md
git commit -m "chore(5): mark accessibility WCAG 2.2 AA delivered; full suites green"
```

- [ ] **Step 7: Finish the development branch**

Use **superpowers:finishing-a-development-branch**. The user's durable convention applies: commits already on `main`; force-sync the tracking branch and push (PR #7 accumulates — no new PR):

```bash
git branch -f claude/lucid-cray-03eff5 main && git push origin claude/lucid-cray-03eff5
```

- [ ] **Step 8: Update programme memory**

Update `/Users/leeashmore/.claude/projects/-Users-leeashmore-Local-Repo/memory/project_investED_programme.md` so sub-project 5 reads DONE with a one-paragraph summary mirroring 4b's, and `MEMORY.md`'s index line is shortened to reflect 1–5 DONE; next = #6 Mobile-first.

---

## Self-Review

**Spec coverage:** §1 (gate) → Tasks 1/2/3. §2 (primitives) → Tasks 4/5/6/7. §3 (remediation surfaces + manual audit) → Task 10 by group + Task 11 cross-cutting + Task 12 manual register. §4 (content model + charts + tests + register) → Tasks 7/8/9/12. Out-of-scope items in the spec are honored (no AAA, no Radix rewrite, no media pipeline, English-only). No gaps.

**Placeholder scan:** No TBD/TODO/"add appropriate". Task 10 is honestly framed as a gate-driven remediation loop (not a placeholder — the per-group acceptance command, allowed fix patterns, and commit messages are concrete). Task 8 contains a conditional ("if there are no video lessons in the seed today…") with a concrete fallback (skip + register row) rather than a hidden gap. Task 11 Step 5's jsdom layout limitation is acknowledged with the Playwright fallback explicitly named.

**Type/name consistency:** `SkipLink`, `useRouteFocus`, `LiveRegion`, `useAnnounce`, `VisuallyHidden`, `Disclosure`, `Field`, `ChartDescription` are named identically across creation tasks, wiring tasks, and tests. `transcript: string` and `captions_available: boolean` match in the backend seed/test (Task 8), the `VideoLesson` prop type (Task 9), and the authoring guide (Task 12). Chart `summary` / `columns` / `rows` props are consistent between `ChartDescription` definition and both chart wirings (Task 7).
