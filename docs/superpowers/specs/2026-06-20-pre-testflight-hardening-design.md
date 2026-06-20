# Pre-TestFlight Hardening — Design Spec

**Date:** 2026-06-20
**Status:** Approved (design); ready for implementation plan
**Scope:** Three independent fixes surfaced in a pre-TestFlight review of session, billing entitlement, and the streak reminder. One spec, three units; each ships and promotes independently.

---

## Context

A pre-TestFlight review of `/Users/leeashmore/investikid` surfaced three issues:
1. **Users are forced to re-login ~every 15 minutes.** The access token TTL is 15 min and the API client never uses the existing 30-day refresh token / `/auth/refresh` endpoint, so any 401 bounces to `/login`. (Face-ID users are covered by `BiometricGate`; everyone else is not.)
2. **`is_premium` can go stale.** Entitlement is a denormalized column set by provider webhooks via `recompute_household_premium`, which entitles on subscription `status` only — it never checks `current_period_end`, and there is no reconciliation for missed/delayed webhooks. A lapsed or un-webhooked subscription can keep premium access.
3. **The daily streak reminder rarely reaches users.** It is a local, native-only notification that is **off by default** and only enabled via a buried ProfileMenu toggle, so engaged kids almost never turn it on.

A fourth concern raised in the same review — Duolingo-style seamless onboarding + native child-initiated purchase via Apple "Ask to Buy" / Google Play family approval — is **decomposed into its own follow-on sub-project** (own spec → plan → build) and is **out of scope here**.

## Goal

Make sessions persist safely, keep premium entitlement honest, and get the streak reminder actually enabled — without weakening per-request security or the kids'-app safety posture.

## Non-goals (deferred / out of scope)

- Onboarding redesign, conditional parent-email collection changes, and native child-initiated purchase / Ask-to-Buy (separate sub-project).
- Changing the parent (`ParentSession`) auth lifetime — it stays separate and short-lived.
- Changing the access-token TTL (stays 15 min, rotating) or the refresh-token TTL (stays 30 days).
- Server push for the streak reminder (the existing FCM streak-at-risk path is unchanged).
- A grace-period **duration** cap on `past_due` (the `current_period_end` guard already bounds it in time).

---

## Unit 1 — Persistent login (refresh-on-401)

**What:** Keep users logged in for up to the 30-day refresh window (indefinitely with regular use) instead of ~15 minutes, with no loss of per-request security.

**Where:** `frontend/src/api/client.ts` (the `apiFetch` wrapper). The backend `/auth/refresh` endpoint (`POST`, cookie-based, CSRF-protected) already exists — **no backend change**.

**How:**
- On a `401` response from any `apiFetch` call, attempt a **single-flight** token refresh: `POST /auth/refresh` (reusing the existing CSRF-header mechanism the client already applies to mutating requests). Concurrent 401s share one in-flight refresh promise rather than each firing their own.
- If the refresh succeeds → **retry the original request once** and return its result transparently.
- If the refresh fails (refresh token missing/expired/revoked) → propagate the 401; the existing `useChildAuthGuard` redirect to `/login` fires as today.
- **Loop guards:** never attempt refresh for the `/auth/refresh` or `/auth/login` calls themselves; retry the original request at most once; a 401 on the retried request is returned as-is (no second refresh).
- **Decoupled from billing:** access TTL stays 15 min and rotates; refresh TTL stays 30 days. A long session never grants premium content — entitlement is checked live server-side on every request (Unit 2). Biometric users are unaffected: `BiometricGate`'s `/biometric/exchange` path continues to re-mint lapsed sessions on cold launch / >2-min background.

**Data flow:** `request → 401 → (single-flight) POST /auth/refresh → 200 → retry request → response` (happy path); `→ refresh 401 → propagate → guard redirects to /login` (give-up path).

**Error handling:** refresh network error or non-200 → treat as give-up (redirect), never loop; the single-flight promise resets after settle so a later 401 can refresh again.

---

## Unit 2 — Subscription freshness

**What:** Ensure `is_premium` reflects an actually-active subscription, even if a period lapses or a provider webhook is missed/delayed.

**Where:**
- `backend/app/services/entitlements.py` — the entitlement predicate.
- New `backend/app/services/subscription_reconcile_service.py` — the daily reconcile.
- A new internal endpoint in `backend/app/routers/internal.py` + a GitHub Actions schedule, mirroring the existing `video-health-cron` / streak-risk pattern (`X-Cron-Secret`, constant-time check, `503` when `CRON_SECRET` unset).

**How:**
- **Guard (correctness, cheap):** in `recompute_household_premium`, entitle a row only when `status ∈ ACTIVE_SUBSCRIPTION_STATUSES` **and** (`current_period_end is None` **or** `current_period_end > now`). An expired-but-`active`/`past_due` row stops entitling immediately. (`current_period_end is None` still entitles, to avoid regressing providers/rows that don't populate it.)
- **Daily reconcile (safety net):** a cron re-pulls **authoritative provider state** for `Subscription` rows whose `current_period_end` is at/after-now-risk (i.e. `current_period_end <= now + small_window` or already past) and whose status is currently entitling:
  - Stripe → `Subscription.retrieve` (reuse the fetch logic in `webhook_service`).
  - Apple → App Store Server API (`apple_billing_service._fetch_status`).
  - Google → Play Developer API (`google_billing_service` fetch).
  Update the stored `status` / `current_period_end` from the provider, then call `recompute_household_premium` for each affected `parent_email`. Re-pulling (vs trusting the stored timestamp) avoids falsely revoking an auto-renewed subscription whose renewal webhook never arrived.
- **Bounded blast radius:** the reconcile is best-effort **per row** — a single provider error is caught, logged server-side, and does not abort the batch. The endpoint returns a small summary (checked / updated / errored counts).

**Data flow:** `cron → POST /internal/subscriptions/reconcile (X-Cron-Secret) → select at-risk rows → per row: re-pull provider → update row → recompute_household_premium(parent_email) → summary`.

**Error handling:** unset `CRON_SECRET` → `503`; bad/expired provider call → caught per row, logged, counted, batch continues; no migration (`current_period_end` already exists on `Subscription`).

---

## Unit 3 — Streak-reminder nudge

**What:** Get the off-by-default, native-only daily streak reminder actually enabled by engaged kids, while respecting the OS permission model (no silent default-on).

**Where:** a small one-time nudge component rendered in the child Home / Shell, reusing the existing `frontend/src/lib/streakReminder.ts`, `frontend/src/lib/reminderConfig.ts`, and the enable logic already in `ProfileMenu.tsx`.

**How:**
- **Native-only** (`isNativeApp()`); a no-op on web.
- Shown **once** to a child who **has a live streak** (`streakCount > 0`, from `useProgress`) and has **not already enabled** the reminder and has **not dismissed** the nudge before (a `localStorage` "nudge seen" flag, distinct from the reminder-enabled key).
- **Accept** → request OS notification permission (`requestReminderPermission`), and on grant enable the reminder toggle (set the existing reminder `localStorage` key) and call `syncStreakReminder`; set the "nudge seen" flag.
- **Dismiss** → set the "nudge seen" flag and never show again. The ProfileMenu toggle remains the manual control either way.
- Reaches devices only via the next TestFlight build (the held native build predates the reminder feature) — which is the upcoming upload.

**Data flow:** `Home mount (native) → streak>0 && !enabled && !nudgeSeen → render nudge → accept → request permission → grant → enable + sync; dismiss/deny → set nudgeSeen`.

**Error handling:** permission denied → set "nudge seen", show the existing "enable notifications in Settings" hint path, never re-prompt; the nudge is permission-gated and self-suppressing.

---

## Testing strategy

- **Unit 1 (client, mocked fetch):** refresh-on-401 then retry succeeds transparently; single-flight (two concurrent 401s → one `/auth/refresh`); retry at most once; refresh failure → propagate 401 (guard redirect); no refresh attempt for the login/refresh calls themselves.
- **Unit 2 (backend):** entitlement truth-table — expired `active` → **not** premium; future `current_period_end` → premium; `null` period → premium (no regression); `past_due` within period → premium, past period → not. Reconcile: a stale row gets flipped after a re-pull; an auto-renewed row (provider says active, later period) is **not** falsely revoked (mock provider); a provider error on one row doesn't abort the batch; `503` when `CRON_SECRET` unset.
- **Unit 3 (frontend, mocked native + progress):** nudge renders only when native + `streak>0` + not-enabled + not-seen; accept requests permission and on grant enables + syncs; dismiss sets the seen flag and suppresses; web renders nothing; a11y (vitest-axe) on the nudge.
- **Full gates:** backend `ruff` + `pytest`; frontend `tsc` + `lint` + `test` + `build`. CI authoritative.

## Definition of done

1. A non-biometric user stays logged in across app opens for the refresh window; a 401 silently refreshes and retries; a truly-expired session still redirects to login.
2. An expired or un-renewed subscription no longer grants premium: the `current_period_end` guard takes effect immediately and the daily reconcile re-pulls provider state to catch missed webhooks — without falsely revoking auto-renewals.
3. An engaged child is nudged once (natively) to enable the streak reminder, with OS permission respected; declining never nags again.
4. No DB migration. All CI jobs green; promoted `testing → staging → main`; Units 1 & 3 need `npm run build && npx cap sync ios`; the reconcile cron uses the existing `CRON_SECRET` + a new GitHub Actions schedule.

## Rollout / safety

- **No DB migration** (`current_period_end` already exists). No prod snapshot question.
- Unit 2 is backend-only; Units 1 & 3 are frontend + iOS sync (web admin/child unaffected on web for Unit 3 — it's native-only).
- Promote `testing → staging → main` on green CI; manual Vercel prod for the web bundle; the reconcile GitHub Actions schedule curls the internal endpoint with `X-Cron-Secret`.

---

## Self-review

- **Placeholders:** none — each unit names its files, seams, predicate, and tests.
- **Consistency:** Unit 1 is client-only (backend `/auth/refresh` exists); Unit 2 guard + reconcile both route through `recompute_household_premium`; Unit 3 reuses the existing reminder lib + adds only a "nudge seen" flag. No unit depends on another.
- **Scope:** focused on the three reviewed issues; onboarding / Ask-to-Buy explicitly deferred to its own sub-project; no migration; no token-TTL changes.
- **Ambiguity:** the `current_period_end is None → still entitled` rule and the reconcile "re-pull vs trust timestamp" choice are stated explicitly to avoid the false-revoke failure mode.
