# Auth-Screen Polish (SP-D2) — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Programme:** "Yasmin's Choice" rebrand — **SP-D part 2** (final layout sub-project before SP-E). SP-0/A/B/C/D1 shipped.

## Goal

Give the auth/account screens the polished sky-blue card look + Penny branding that the rest of the app has, by enhancing the **one shared `AuthPage` wrapper** and adopting it across all auth screens. **Layout/structure only** — no behaviour, route, validation, data, or copy-logic change. Colour was already done by SP-A's sweep; this is structure + branding.

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

**3. Per-screen titles** (move existing copy into `title`): Login "Sign in to InvestiKid" → `title="Welcome back"`-style is a copy change — **DO NOT change copy**; pass the screen's *existing* heading text as `title`. (E.g. Login keeps "Sign in to InvestiKid", ParentLogin keeps "Parent sign-in", etc.)

## Accessibility

- Exactly one `<h1>` per screen (the `AuthPage` `title`); if a screen had an `<h1>` inside content, demote/remove the duplicate.
- Inputs stay ≥16px on touch (shadcn `Input` + the global coarse-pointer rule); visible focus; error messages keep `role="alert"`.
- Keep `viewport-fit=cover` + the safe-area padding `AuthPage` already applies. Penny/logo decorative → `aria-hidden`.

## Out of scope

`ParentAuthCallback` (transient redirect — only touch if it renders visible chrome worth carding). No new auth flows, no copy rewrites, no validation changes. Settings `SignInMethods` (already carded in D1) — leave as is.

## Testing

- `AuthPage`: unit (renders header/title/card) + `vitest-axe`.
- Updated screens: adapt existing tests to the new structure (heading now comes from `AuthPage`); keep all behavioural assertions (submit, validation, error, social buttons, magic-link). Before/after mocked screenshot of Login + ParentLogin.
- `tsc -b`, lint, test, build; backend untouched. All 5 CI jobs green. iOS rebuild deferred to programme end.

## Plan shape

T1 enhance `AuthPage` + test → T2 adopt in child Login/Signup/PendingConsent → T3 adopt in ParentLogin (+ keep social buttons) + ForgotPassword/ResetPassword → T4 adopt in VerifyEmail/ConsentVerify → T5 a11y + regression + push. Each a green-CI checkpoint.

## Decisions captured

Enhance the shared `AuthPage` (Penny + "InvestiKid" wordmark header + white card) and adopt across all 8 auth screens · layout-only, no copy/behaviour change · one `<h1>` per screen via `title`.
