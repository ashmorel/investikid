# SP-E — Parent / Admin Sky-Blue + Penny Polish — Design

**Status:** Approved (design), pending spec review.
**Date:** 2026-06-04
**Context:** Final sub-project of the "Yasmin's Choice" rebrand (SP-0/A/B/C/D1/D2/F shipped; Country/Region switcher shipped). Brings the **parent dashboard** and **admin panel** onto the sky-blue/Penny identity. **Layout-only** — no API, data model, or behaviour changes.

## Goal

Make the two remaining off-brand surfaces match the app's established sky-blue + Penny identity:
1. **Parent dashboard** — replace the stale "IE" monogram with Penny + wordmark and lightly polish spacing/states. (Already mostly brand-aligned post-SP-A.)
2. **Admin panel** — convert the dark slate theme to the light sky-blue/card aesthetic used everywhere else. (Never received the SP-A sweep; 18 files carry ~370 dark-class occurrences.)

## Constraints (load-bearing)

- **Layout-only.** No changes to routes, API calls, data shapes, admin CRUD behaviour, or auth/guards. Every existing query, mutation, and form submission keeps working unchanged.
- **Reuse existing semantic tokens** (`brand-*`, `accent-*`, `success-*`, `danger-*`, `surface`, `ink`/foreground, `muted-foreground`, `line`, `bg-brand-gradient`). No new tokens, no `tailwind.config.js` (Tailwind v4 CSS-first).
- **WCAG 2.2 AA.** The light admin theme must meet contrast (the dark theme leaned on low-contrast `slate-400`). Touch targets ≥44px where interactive; inputs ≥16px (`text-base`) — admin is desktop-first but the rule still holds. No `maximum-scale`.
- Keep the admin **emoji nav icons** (out of scope to introduce an icon set — YAGNI).
- Reuse the existing `Penny` mascot component (`{size, mood, className}`); no new mascot art.

## Workstream A — Parent dashboard (light polish)

**File:** `src/pages/ParentDashboard.tsx` (+ no others; `ChildCard`, `SubscriptionCard`, `SignInMethods` are already brand-aligned and untouched; `ParentLogin` was branded in SP-D2).

- Replace the **`IE` gradient monogram** (`<Link to="/parent">…IE…</Link>`) in the sticky header with the `Penny` mascot (small) + an "InvestiKid" wordmark, matching the branded auth header pattern. The link target (`/parent`) and the sticky/backdrop header behaviour stay.
- Tidy header/card spacing for rhythm consistency with the child app.
- Friendlier **empty / loading / error** copy: e.g. empty state "No children linked to this account." → a warmer, on-brand line (still factual, no new actions). Loading and `ErrorBanner` keep their roles; just spacing/tone.
- No structural/layout reshape, no new sections.

## Workstream B — Admin panel (dark → light sky-blue)

The core is **one documented dark→light class mapping**, applied consistently across all 18 admin files so the panel is coherent (a half-converted panel reads as broken):

| Dark (current) | Light (target) |
|---|---|
| `bg-slate-950` (page) | app page background (`bg-background` / the app's neutral page bg) |
| `bg-slate-900` (cards, sidebar) | `bg-card` / `surface` (white card) |
| `border-slate-700/800` | `border-line` (or `border-brand-100` for branded edges) |
| `text-slate-50/100` (headings) | `text-foreground` / `ink` |
| `text-slate-300/400/500` (body/muted) | `text-muted-foreground` (verify AA on white) |
| `bg-blue-600` (active nav / primary) | `bg-brand-gradient` (nav active) / `brand-600` (primary) |
| `hover:bg-slate-800` | `hover:bg-brand-50` |
| stray `text-blue-400`, mixed semantic | correct semantic token (`brand-*`/`info-*`/`success-*`) |
| form inputs on dark | the app's standard light input style (`border-input`, `bg-background`, `text-base`) |

**Surfaces (most design attention on the shell):**
- **Shell:** `AdminLayout` (light page bg + loading state), `AdminSidebar` (light sidebar, brand-gradient active item, emoji kept), `AdminDashboard` (light stat cards).
- **Settings & lists:** `AdminSettings`, `ModuleList`, `LevelList`, `LevelLessonList`, `BadgeList`, `ChallengeList`, `FeedbackList`, `ModuleEngagement`.
- **Forms:** `ModuleForm`, `LessonForm`, `BadgeForm`, `ChallengeForm`, `LevelForm` (the heaviest — LessonForm 58 / ModuleForm 51 / ChallengeForm 42 dark-class hits).
- **Shared:** `ConfirmDialog`, `OrderArrows`.

The mapping is defined once (in the plan and applied uniformly); per-file work is the mechanical substitution plus visual sanity per screen.

## Out of scope

- New admin features, icon-set swap, table redesign, dark-mode toggle, any backend/API/data change.
- Re-theming `ChildCard`/`SubscriptionCard`/`ParentLogin`/auth screens (already done).
- The `country_code`-immutability hardening (shipped separately, commit `ea3370e`).

## Testing

- Keep all **13 existing admin component tests** green; update any that assert on old `slate-*`/`blue-*` classes to the new tokens (assert on role/text/behaviour where possible rather than exact colour classes).
- `vitest-axe` contrast/a11y check on the converted **shell + dashboard** (and any list/form test that already runs axe).
- `npx tsc -b` clean; `npm run lint` clean apart from the known pre-existing `button.tsx` + `Market.tsx` react-refresh warnings; `npm test` all pass; `npm run build` succeeds.
- All 6 CI jobs green (frontend, backend, security, a11y, responsive, iOS Capacitor). This is web/parent-admin only — no iOS-visible child change, so no `npx cap sync ios` needed.

## Plan shape (build order)

1. **Parent dashboard** (small, self-contained: Penny header + spacing/states) → commit.
2. **Admin shell** (`AdminLayout` + `AdminSidebar` + `AdminDashboard`) — establishes the light look + the mapping in practice → commit.
3. **Admin lists + settings** (Module/Level/LevelLesson/Badge/Challenge/Feedback lists, ModuleEngagement, AdminSettings) → commit(s).
4. **Admin forms** (Module/Lesson/Badge/Challenge/Level) — the bulk → commit(s).
5. **Admin shared** (ConfirmDialog, OrderArrows) + **a11y/contrast pass** + full regression → push, green CI.

Each step verifies tsc + lint + test + build before committing; the heavy form step may split into two commits.

## Decisions captured

- **Admin → light sky-blue** (full brand consistency), not branded-dark or skip. Comprehensive across all 18 files in this one sub-project (no forms-deferral) so the panel is never half-converted.
- **Parent → Penny + light polish** (replace "IE" monogram, tidy spacing/states), not a deeper hero restyle.
- Emoji nav icons kept. Layout-only; reuse existing tokens + `Penny`. WCAG 2.2 AA enforced via `vitest-axe` on the converted shell/dashboard.
