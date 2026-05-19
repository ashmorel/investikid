# Accessibility (WCAG 2.2 AA) — Design Spec (Sub-project 5)

**Status:** Approved (brainstorming) — 2026-05-19
**Programme:** Invest-Ed hardening, sub-project 5 (follows 4b; sub-projects 1–4 DONE)
**Working dir:** `/Users/leeashmore/Local Repo/invest-ed`

## Goal

Bring every user-facing surface of Invest-Ed to WCAG 2.2 Level AA conformance, and
keep it there with a CI-enforced automated gate plus a documented manual audit and
conformance register — mirroring how sub-project 2's security CI gate is run.

## Context (verified against the frontend)

Stack: React + TS + Vite + Tailwind; shadcn-style primitives in
`frontend/src/components/ui/*` are **Radix-based** (dialog, dropdown-menu, switch,
label, tooltip, toast, sheet) and already carry correct semantics. Existing
foundation: `index.html` has `<html lang="en">`; child `Shell.tsx` renders a
semantic `<main>`; `TopNav` has `<header>` + `<nav aria-label="Primary">`;
`BottomTabBar` has `<nav aria-label="Primary mobile">`; Login/Signup use
`htmlFor`/`id` labels, `aria-invalid`, and `role="alert"` errors;
`ErrorBanner.tsx` uses `role="alert"`; `QuizLesson` is a keyboard-operable
`role="radiogroup"`; `TradeForm` uses `role="radio"`/`aria-checked`/`aria-live`.

Verified gaps: **no a11y tooling** (no `eslint-plugin-jsx-a11y`, no axe in tests —
Vitest 3 + Playwright 1.49 + Testing Library present but not a11y-focused); **no
skip-link**; **no focus management / announcement on route change** (Framer Motion
transitions, `useLocation()` but no focus reset); **unlabelled native `<select>`s**
in Signup; **Recharts charts** (`PortfolioChart`, `StockChart`) have no text
alternative; **VideoLesson** (YouTube iframe, `title` set) has no caption track or
transcript; **color contrast unaudited** (blue/purple/amber badge pairs, focus
ring); inline SVG illustrations lack `role="img"`/label; no `prefers-reduced-motion`
handling for route/page animation; WCAG 2.2-new criteria (target size 2.5.8,
focus-not-obscured 2.4.11) unverified.

## Approach (chosen)

**Layered (Approach A):** land the regression net first, then build shared a11y
primitives once, then remediate surfaces against the now-failing gate plus a manual
audit, then ship the conformance register. The gate exists before fixes so progress
is measurable and regressions are caught immediately; primitives are DRY.

---

## Section 1 — Tooling & CI gate

- **`eslint-plugin-jsx-a11y`** added to `frontend/eslint.config.js` (flat config)
  at its `recommended` ruleset, registered alongside `react-hooks`/`react-refresh`.
  `npm run lint` fails on a11y violations.
- **`vitest-axe`** dev dependency; `toHaveNoViolations` registered in the existing
  vitest setup file. New `frontend/tests/a11y/` holds per-surface axe tests that
  render pages/critical components via the existing Testing Library render helpers
  and assert zero violations.
- **`@axe-core/playwright`** e2e spec driving the key authenticated flow
  (signup → home → a lesson → simulator trade → stats), asserting no
  serious/critical violations against the running app.
- **CI:** extend `.github/workflows/ci.yml` so lint + vitest-axe run in the
  `frontend` job and the Playwright axe scan runs in the existing e2e stage. A
  dedicated `a11y` job (mirroring the security-gate job) is acceptable if cleaner.
- **Fail policy:** axe `serious`+`critical` and all `jsx-a11y` `recommended`
  errors **block the build**. `moderate`/`minor` axe findings are logged into the
  conformance register for manual triage, not auto-failed (keeps the gate
  authoritative without heuristic flaking).

## Section 2 — Shared a11y primitives

Under `frontend/src/components/a11y/` (+ one hook), each single-responsibility,
independently tested (vitest + vitest-axe), reused everywhere:

- **`SkipLink`** — visually-hidden-until-focused "Skip to main content" anchor at
  the top of the child `Shell` and the parent layout; `<main>` gets `id="main"` +
  `tabIndex={-1}`. (2.4.1)
- **`useRouteFocus`** — on Router location change, moves focus to the main
  heading and announces the page title via a polite live region. (2.4.3, 4.1.3)
- **`VisuallyHidden`** — canonical `sr-only` component; replaces ad-hoc usages.
- **`LiveRegion` / `useAnnounce`** — one app-level polite `aria-live` region +
  setter for async state not covered by existing `role="alert"`.
- **`ChartDescription`** — from a chart's series + meta renders an SR summary
  sentence + a `VisuallyHidden` marked-up `<table>` of points. Consumed by both
  charts. (1.1.1)
- **`Disclosure`** — accessible expand/collapse (button + `aria-expanded`/
  `aria-controls`); used for the video transcript. If a Radix `Collapsible` is
  already available, wrap it instead (implementer checks).
- **`Field`** — standardises `<label htmlFor>` + control + error
  (`aria-invalid`, `aria-describedby`, `role="alert"`); gives the unlabelled
  Signup `<select>`s proper labels. Existing accessible Login/Signup patterns are
  folded in, not rewritten.

Radix UI primitives are **not** rebuilt; only usage gaps surfaced by the
gate/audit are fixed.

## Section 3 — Remediation surfaces & manual audit method

**Surface groups** (fixed together against the gate):

- *Auth & entry:* Signup (unlabelled `<select>`s → `Field`), Login,
  PendingConsent, ConsentVerify, VerifyEmail, ForgotPassword, ResetPassword,
  Privacy, ParentLogin, ParentAuthCallback.
- *Child core:* Home, Lessons, Module, Lesson, Stats — landmarks, heading order,
  focus, name/role/value on cards/rows.
- *Lesson renderers:* Card, Video (transcript `Disclosure`), Scenario, Quiz,
  Practice — keyboard, focus, badge contrast.
- *Simulator:* Simulator, TradeForm, HoldingsTable (table semantics),
  PortfolioChart/StockChart (`ChartDescription`), MarketSearchBar
  (combobox/listbox semantics), MarketNews/StockNews + news widgets.
- *Parent:* ParentDashboard (its child cards & any charts).
- *Cross-cutting:* contrast token audit (blue/purple/amber badge pairs, focus
  ring → ≥4.5:1 text, ≥3:1 UI/focus via Tailwind token/class changes);
  `prefers-reduced-motion` for Framer Motion route/page transitions
  (2.3.3, 2.2.2); WCAG 2.2-new target-size 2.5.8 and focus-not-obscured 2.4.11
  on tap targets and sticky nav.

**Manual audit method** (documented in the conformance register, not just axe):

- **Keyboard-only:** all interactive elements reachable/operable, visible focus,
  logical order, no traps, skip-link works.
- **Screen reader:** VoiceOver (macOS/Safari) as reference AT; sample each
  surface group — names/roles/states, live-region announcements,
  chart/transcript consumability, form/error clarity.
- **WCAG 2.2 AA checklist:** each applicable A/AA success criterion marked
  Pass/Fail/N-A per surface group with notes; failures → remediation items;
  source-dependent/non-applicable items recorded with rationale.
- **Zoom/reflow:** 200% zoom + 320px reflow (1.4.10), text-spacing (1.4.12).

## Section 4 — Content model, charts, testing, register

**Video transcript:** video-lesson `content_json` gains optional
`transcript: string` and `captions_available: boolean`. **No DB migration** —
`Lesson.content_json` is free-form JSON; backend `LessonOut` passes it through.
`VideoLesson` renders the transcript in the `Disclosure` when present and a
"Captions available / No captions" indicator from the flag. Seeded video lessons
in `backend/app/seed/content.py` get transcript text + `captions_available`. A
backend test asserts every seeded video lesson carries a non-empty `transcript`.
Content policy (docs): only captioned YouTube sources; every video lesson must
ship a transcript.

**Charts:** `PortfolioChart`/`StockChart` wrap the Recharts SVG with
`role="img"` + `aria-label` (summary sentence) and render `ChartDescription`
(hidden table + summary) from series already in props. No new data plumbing.

**Testing:**
- Each new primitive: vitest + vitest-axe.
- Each remediated surface group: a vitest-axe zero-violations test + targeted
  RTL keyboard/role assertions for the specific fixes.
- Playwright `@axe-core/playwright` scan over the key flow.
- Backend suite stays green (only seed-content + one seed assertion change);
  frontend suite grows and stays green; CI a11y gate green.

**Docs / register:**
- `frontend/docs/accessibility/conformance-2026-05.md` (mirrors
  `docs/security/audit-2026-05.md`): scope, WCAG 2.2 AA criterion-by-surface
  Pass/Fail/N-A matrix, manual keyboard/SR findings, residual/source-dependent
  items with rationale, how the automated gate enforces it ongoing.
- `frontend/docs/accessibility/authoring-guide.md`: video-transcript/
  captioned-source content policy + a11y primitive usage.
- Close-out: mark spec Delivered, commit to `main`, force-sync
  `claude/lucid-cray-03eff5` and push (PR #7 accumulates — no new PR), update
  programme memory.

## Out of scope

- WCAG 2.2 AAA criteria.
- Backend/API accessibility beyond passing `content_json.transcript` through
  (no schema migration; it's free-form JSON).
- Re-authoring Radix UI primitives (semantics already correct).
- Producing/hosting our own captioned video files or a media pipeline (policy +
  transcript instead; third-party YouTube caption quality recorded as a
  source-dependent residual item).
- Internationalisation/localisation (English-only app today).
- Native mobile (sub-project 6, Mobile-first).
- Re-doing sub-projects 1–4.
