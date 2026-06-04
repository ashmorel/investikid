# Auth-Screen Polish (SP-D2) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-D part 2** (final layout sub-project before SP-E). SP-0/A/B/C/D1 shipped.

## Goal

Three friendly-polish items bundled: **(1)** give the auth/account screens the polished sky-blue card look + Penny branding via the shared `AuthPage`; **(2)** warm up the auth-screen **copy** (headings/labels/helper/error text); **(3)** make the global **Coach Penny** button open an in-context slide-over panel instead of navigating to a full page. No validation/data/route-contract change (the `/coach` route stays); form submit logic and the chat behaviour are preserved.

## Current state (verified)

- `src/components/AuthPage.tsx` is a bare centered, safe-area-aware, `max-w-md`, overflow-guarded wrapper — **no card, no branding**. Only **`child/Login.tsx`** and **`child/Signup.tsx`** use it; their content is a plain `<h1>` + form.
- Six auth screens roll their **own** containers (inconsistent): `ParentLogin.tsx`, `ForgotPassword.tsx`, `ResetPassword.tsx`, `VerifyEmail.tsx`, `ConsentVerify.tsx`, `child/PendingConsent.tsx`.
- `Penny` mascot is at `src/components/child/ui/Penny.tsx` (`{size,mood,className}`). `ParentAuthCallback.tsx` is a transient redirect screen (minimal; out of scope unless it shows visible chrome).

## Design

**1. Enhance `AuthPage`** into a branded auth card (presentational wrapper; keep the existing centered layout + safe-area padding + overflow guards + `max-w-md`):
- New optional props: `title?: string`, `subtitle?: string` (alongside `children`, `className`).
- Renders, centered on the `surface` background:
  - a **brand header** — `Penny` avatar (size ~44, `mood="happy"`) in a soft `bg-brand-100` circle + the **"InvestiKid" wordmark** (extrabold, `text-ink`); then the optional `title` (`<h1>`, consistent size) + `subtitle` (`text-muted-foreground`).
  - the `children` inside a **card**: `rounded-2xl border border-brand-100 bg-card p-6 shadow-sm`.
- Decorative Penny + logo glyphs `aria-hidden`; the wordmark is real text. `AuthPage` gets a `vitest-axe` test (renders header + card + a single `<h1>` when `title` set).

**2. Adopt `AuthPage` across all 8 screens.** For the 6 that don't use it, wrap their content in `<AuthPage title="…">`, removing their bespoke outer container and moving their existing `<h1>` text into the `title` prop (so there's one consistent heading). Keep **everything else** intact: form fields, validation, submit mutations, error `role="alert"` messages, the magic-link flow, and the D1 "Continue with Apple/Google" buttons on `ParentLogin`. Login/Signup automatically gain the card + header (they already use `AuthPage`); move their `<h1>` text into the `title` prop too and de-duplicate.

**3. Friendlier copy.** Each screen's heading moves into the `AuthPage` `title` and gets a warmer, kid/parent-friendly tone, with a short `subtitle` where it helps. Tasteful, plain-English, encouraging — not jokey. Examples (illustrative; implementer may refine): Login `title="Welcome back!"` `subtitle="Let's keep learning."`; Signup `title="Let's get you set up"`; ParentLogin `title="Parents' sign-in"` `subtitle="Manage your child's account."`; ForgotPassword `title="Forgot your password?"` `subtitle="We'll email you a reset link."`; VerifyEmail/ConsentVerify/PendingConsent get reassuring, parent-friendly wording. **Constraints:** only human-readable copy changes — never change field names, `id`/`htmlFor`, validation logic, error semantics, or route/redirect behaviour. Error messages may be softened but must stay clear and `role="alert"`.

### Coach Penny floating panel

Make the global `PennyFAB` open Coach Penny **in an in-context slide-over** instead of navigating to `/coach`:
- **Extract** the chat body from `src/pages/child/Coach.tsx` into a reusable **`CoachChat`** component (the greeting + messages + suggestion chips + input + `aiApi` send mutation + remaining/error states). It accepts an optional `onNavigate?: () => void` called when an action-link is followed (so the panel can close). Pure relocation — no behaviour change.
- **`CoachPanel`** — a slide-over built on the existing `src/components/ui/sheet.tsx` (Radix Dialog → focus-trap, ESC-to-close, `aria-modal`, focus return for free): a right-side sheet (full-width on small screens) with a header (Penny avatar + "Coach Penny") wrapping `<CoachChat onNavigate={close} />`.
- **`Shell`** holds `coachOpen` state and renders `<CoachPanel open={coachOpen} onOpenChange={setCoachOpen} />`. **`PennyFAB`** changes from internal `navigate('/coach')` to an `onOpen: () => void` prop; Shell passes `() => setCoachOpen(true)`. The FAB's `dueCount` badge + aria-label stay.
- **Keep the `/coach` route** — `Coach.tsx` becomes a thin page rendering `<CoachChat />` full-screen (direct links / deep links still work). Action-links inside the panel navigate **and** close the panel; in the full page they just navigate.
- A11y: the sheet traps focus, closes on ESC + overlay click, returns focus to the FAB; the chat input stays ≥16px.

## Accessibility

- Exactly one `<h1>` per screen (the `AuthPage` `title`); if a screen had an `<h1>` inside content, demote/remove the duplicate.
- Inputs stay ≥16px on touch (shadcn `Input` + the global coarse-pointer rule); visible focus; error messages keep `role="alert"`.
- Keep `viewport-fit=cover` + the safe-area padding `AuthPage` already applies. Penny/logo decorative → `aria-hidden`.

## Out of scope

`ParentAuthCallback` (transient redirect — only touch if it renders visible chrome worth carding). No new auth flows, no validation changes, no field/route-contract changes. App-wide copy warming beyond the auth screens (this round's copy pass is scoped to auth/account). Settings `SignInMethods` (already carded in D1) — leave as is. The Coach **chat logic/endpoints** are unchanged — only its presentation moves into a panel.

## Testing

- `AuthPage`: unit (renders header/title/card) + `vitest-axe`.
- Updated screens: adapt existing tests to the new structure (heading now comes from `AuthPage`); keep all behavioural assertions (submit, validation, error, social buttons, magic-link). Before/after mocked screenshot of Login + ParentLogin.
- `tsc -b`, lint, test, build; backend untouched. All 5 CI jobs green. iOS rebuild deferred to programme end.

## Testing (addition for the Coach panel)

`CoachChat` keeps the existing Coach tests' behaviour (greeting, send, chips, action-links, error) — adapt them to the extracted component; add a test that the FAB opens the panel and ESC/overlay closes it (focus returns to the FAB). `/coach` full page still renders `CoachChat`.

## Plan shape

T1 enhance `AuthPage` + test → T2 adopt in child Login/Signup/PendingConsent (+ friendly copy) → T3 adopt in ParentLogin (+ social buttons) + ForgotPassword/ResetPassword (+ copy) → T4 adopt in VerifyEmail/ConsentVerify (+ copy) → T5 extract `CoachChat` + thin `/coach` page → T6 `CoachPanel` sheet + wire FAB/Shell → T7 a11y + regression + push. Each a green-CI checkpoint.

## Decisions captured

Enhance the shared `AuthPage` (Penny + "InvestiKid" wordmark header + white card) across all 8 auth screens · **friendlier auth copy** (warmer headings/subtitles/labels; no field/validation/route change) · **Coach Penny opens an in-context slide-over panel** (FAB → sheet; `/coach` route kept; chat logic unchanged) · one `<h1>` per screen via `title` · bundled into one round.
