# Parent Dashboard Access & Discovery — Design Spec

**Date:** 2026-06-14
**Status:** Approved (brainstorming) → ready for implementation plan
**Scope:** Access & discovery of the existing parent dashboard, light dashboard polish, and closing the free-premium leak. **Not** a rebuild of the dashboard's features.

## Problem

A "parent" in InvestiKid is not an account — it is an **email address** that a child listed in `users.parent_email`. Parent access to the dashboard is minted on demand from proof of inbox ownership (magic link at `/parent/login`, or Apple/Google whose verified email matches a child's `parent_email`). Consequences today:

1. **No discoverable path.** A parent who only ever clicked a one-time consent link has no obvious way to know the dashboard exists or how to return to it.
2. **Logged-in parents are stranded.** A user signed into their own learner account whose email *is* a child's `parent_email` (e.g. an adult who set up their kid) sees nothing telling them they're also a parent — the parent dashboard uses a separate session.
3. **Free-premium leak.** The dashboard's per-child "Premium" switch (`POST /parent/children/{id}/premium` → `set_premium`) flips `users.is_premium` directly with **no payment check**, gated only by "are you this child's parent." It also conflicts with real billing: `recompute_household_premium` overwrites `is_premium` from actual `Subscription` rows, so a manual grant is silently wiped on the next recompute. Widening dashboard access makes this leak critical.

## Goal

Make the existing parent dashboard **obvious and frictionless** to reach — whether the parent set things up, only consented, or is already logged in — without introducing parent accounts or a new auth system, and without giving away free premium.

## Security invariant (the foundation)

> A `parent_session` for email `E` is granted only to a requester who has proven they control inbox `E`.

The dashboard can grant premium, toggle Face ID, export data, and **delete the child's account**, so this bar is non-negotiable. Three **equivalent** proofs of inbox control, all minting the *same* existing 7-day, revocable `parent_session` and reusing the *same* `/parent/*` endpoints:

| Proof | Status |
|---|---|
| Clicked a one-time token emailed to `E` — magic-link login | exists |
| Verified Apple/Google identity whose email is `E` | exists |
| Approved a child via the consent link emailed to `E` (Door 2) | **new** |
| Logged-in user whose **`email_verified_at` is set** and whose email is `E` (Door 1) | **new** |

**Hard gate:** the logged-in bridge requires a **verified** user email. Email verification at registration already required clicking a link sent to that inbox, so a verified-email user is proven to control it. An **unverified** user email never grants parent access.

## Components ("three doors, one dashboard")

### Door 1 — Logged-in parent bridge
- **Backend**
  - `UserProfile` / `GET /users/me` gains `is_parent: bool` = `user.email_verified_at is not None AND EXISTS(child WHERE child.parent_email == user.email AND child.deleted_at IS NULL)`.
  - New `POST /parent/auth/from-session`: authed by the **user** session (`get_current_user`). Requires `current_user.email_verified_at` set **and** ≥1 matching non-deleted child; otherwise **403**. On success, mints a `parent_session` for `current_user.email` via the existing `issue_parent_session` and sets the `parent_session` cookie. CSRF-exempt is **not** required (it carries the user session; treat like other authenticated mutations — include in CSRF like normal session endpoints).
- **Frontend**
  - When `me.is_parent`, the child app surfaces a "Parent area / Manage my children" entry (in `ProfileMenu`, and optionally a dismissible first-run banner).
  - Activating it calls `from-session`, then navigates to `/parent`.

### Door 2 — Consent → session
- **Backend**: in `POST /consent/decide`, on **approve** (after activating the child + existing `parent_consent_given_at` / `guardian_attested_at` stamps), mint a `parent_session` for the child's `parent_email` and set the cookie on the response. Decline path unchanged. The consent token already proved inbox ownership.
- **Frontend**: `ConsentVerify` on approve redirects into `/parent` with a welcoming first-visit state ("Yasmin's all set — here's where you manage her"), replacing the terminal "your child can now sign in" dead-end.

### Door 3 — Discoverable parent login
- Child login screen (`/login`) gains a low-key "Are you a parent? Manage your child →" link to `/parent/login`.
- The **weekly digest email** (already sent to the parent) links to the dashboard (`/parent`) — verify/add the link.
- The post-consent screen tells parents they can return any time at `app.investikid.ai/parent`.

### Door 4 — Light dashboard polish
- Friendlier empty state on `ParentDashboard` when `/parent/children` is `[]`: explain the likely cause ("No child is linked to this email — make sure your child entered **this** address as their parent's email") instead of the bare "No children linked…".
- A one-time, dismissible first-visit welcome hint summarising what a parent can do (notifications, premium/subscription, safety, data).

### Door 5 — Close the premium leak
- **Frontend**: `ChildCard` removes the free "Premium" switch and instead shows **subscription status + a Subscribe / Manage action** (reusing the existing `SubscriptionCard` flow / `GET /billing/plans`). Premium shown to parents reflects real entitlement only.
- **Backend**: **remove** `POST /parent/children/{id}/premium` from the parent surface — parents subscribe, they do not grant. Admin/CLI comp granting continues via `set_premium` (admin console + the `grant-premium` CLI); if there is no existing admin HTTP route for it, the plan adds one under `/admin/*`. On the parent surface, premium is written **only** by subscription recompute. The existing premium-**request** flow (parent requests → admin approves/declines) is out of scope and unchanged.

## Data flow & error handling

- `from-session`: unverified email → 403 `email_not_verified`; verified but no matching child → 403 `not_a_parent`. Only ever invoked when `me.is_parent` is true, but defends server-side regardless.
- Consent approve already 410s on an already-decided token; minting the session happens only on a fresh approve.
- All doors yield the identical `parent_session`; revocation, expiry (7 days), and every `/parent/*` authorization (`get_current_parent`, scoped by `parent_email`) are unchanged.

## Testing

**Backend (pytest, async session fixtures):**
- `from-session` mints a parent session for a verified-email parent with ≥1 child; 403 on unverified email; 403 on verified user with no child listing their email.
- `/me.is_parent` true only for verified email matching a child's `parent_email`; false otherwise.
- Consent approve sets the `parent_session` cookie and activates the child; decline unaffected.
- `POST /parent/children/{id}/premium` as a plain parent → 403; as admin → grants (or grant moves to an admin route); subscription recompute remains the only parent-surface premium writer.

**Frontend (vitest + vitest-axe):**
- "Parent area" entry renders iff `me.is_parent`; activating it calls `from-session` then navigates to `/parent`.
- `ConsentVerify` approve → redirect to the dashboard welcome state.
- Child login shows the "Are you a parent?" link; `ChildCard` shows subscription status/Subscribe, **not** a free premium toggle.
- Friendlier empty-state copy renders on zero children; axe clean on all new UI.

## Out of scope

- Persistent parent accounts / parent passwords (kept email-only by design).
- Dashboard feature changes beyond the empty state + welcome hint.
- The premium-request flow; the admin console's own premium tooling.
- Parent-led multi-child signup wizard (Approach C — not chosen).
