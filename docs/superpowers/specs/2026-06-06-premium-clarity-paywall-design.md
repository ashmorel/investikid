# Free vs Premium Clarity + Paywall (Item 4B) — Design Spec

**Date:** 2026-06-06
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Parent backlog item:** premium content & pricing — sub-project **4B**
**Sequence:** 4D ✅ → **4B (this)** → 4A (multi-channel payments) → 4C (subscription nudges)

## Goal

Make it obvious everywhere what's free and what's premium, and replace today's dead-ends
(a bare `403` or a weak "ask a grown-up" toast) with one friendly, consistent **paywall** that
routes a curious child to the parent who can subscribe. 4B is the **clarity + paywall surface** —
it does **not** add payments (4A) or scheduled nudges (4C), and it changes no `is_premium` gating.

## Current state (what exists)

- Per-child `User.is_premium`; single entitlement seam `is_premium()`/`set_premium()`.
- Gates today:
  - `GET /modules` → `200` + `locked` flag per module.
  - `GET /modules/{id}/levels` → `200` + per-level `state` + `locked_reason` (`premium`|`progression`).
  - `GET /modules/{id}/lessons`, `GET /levels/{id}/lessons` → **bare `403`** "…requires premium".
  - Simulator `POST /portfolio/trades` → **bare `403`** "Ticker not available on free tier" for
    non-free tickers when not premium.
  - `POST /home-greeting` → **bare `403`** "Premium required"; tutor/coach degrade silently.
  - `Challenge.is_premium` flag returned, no gating.
- Child UX at a lock today: dimmed module tile / lock icon + a **toast** "Ask a grown-up to unlock";
  Level-lessons `403` → static "This level is premium" text. **No paywall, no parent bridge.**
- Parent: `SubscriptionCard` on the dashboard (web Stripe; suppressed on native per App Store 3.1.1).
- Email infra: `app/services/email.py` — `get_email_sender().send(session, to, template, context,
  subject_id=None)` (async; `LoggingEmailSender` in dev/test, `ResendEmailSender` in prod);
  `SentEmail` model logs every send.

## Approved decisions

1. **Conversion path:** a friendly paywall that lets the child **notify the parent**.
2. **Scope:** **comprehensive** — every gated surface (modules, levels, premium challenges,
   premium simulator tickers, AI coach/home-greeting) gets the same premium marker + paywall.
3. **Notify channel:** **email to the parent + a parent-dashboard flag**, frequency-capped.
4. **Form:** one **reusable bottom-sheet** paywall (reusing the `CoachPanel`/shadcn `Sheet` pattern).

---

## Section 1 — Unified premium vocabulary + the paywall (frontend)

- **`PremiumBadge`** (`src/components/child/PremiumBadge.tsx`) — the single "Premium ✨" marker,
  generalising today's `TierBadge` (`bg-accent-100 text-accent-700` + ✨ + the word "Premium", so
  status is never colour-only). Placed on: locked module tiles, premium level cards, premium
  challenge cards, premium simulator tickers, the AI-coach entry.
- **`PremiumPaywall`** (`src/components/child/PremiumPaywall.tsx`) — a reusable bottom-sheet built on
  the same shadcn `Sheet`/`SheetContent` (Radix dialog, focus-trapped, `SheetTitle`/`SheetDescription`,
  safe-area padding) the `CoachPanel` uses. Contents: Penny, **"Premium unlocks…"** + the canonical
  benefits list, a primary **"Ask my grown-up to unlock"** button, a quiet "Maybe later". On primary
  tap it calls `POST /premium/request` (Section 2) and flips to a confirmation state
  ("We've let your grown-up know! 🎉" / "We already told them today 👍"). **Never** shows price or a
  purchase button to the child (Section 4 — Apple).
- **`usePremiumPaywall()`** (`src/hooks/usePremiumPaywall.tsx`) — a small context/provider exposing
  `open({ kind, label, id? })` where `kind ∈ {module, level, challenge, ticker, coach}`, so any
  surface opens the sheet with the specific content named (and that context is sent to the parent).
- **`src/lib/premiumConfig.ts`** — canonical benefits list + paywall copy (single source for the FE).

**Accessibility:** sheet inherits the existing dialog a11y; `PremiumBadge` carries text + glyph;
WCAG 2.2 AA throughout.

---

## Section 2 — Child→parent request + parent visibility (backend)

- **New model `PremiumRequest`** (`app/models/premium_request.py`): `id`, `child_user_id`
  (FK `users.id`), `parent_email` (str, indexed), `context_kind` (str), `context_label` (str),
  `created_at`, `resolved_at` (datetime | None). Exported from `app/models/__init__.py`. One
  hand-written chained Alembic migration (check `alembic heads` first; current head `c1d2e3f4a5b6`).
- **`POST /premium/request`** (child-auth via `get_current_user`; new `app/routers/premium.py`):
  body `{ kind, label, id? }`. Behaviour:
  1. If the child has no `parent_email` → friendly no-op response (`{status: "no_parent"}`).
  2. Always upsert/record interest; **frequency cap** (`PREMIUM_REQUEST_EMAIL_COOLDOWN`, default
     24h, in `premium_config.py`): only send the email if no email for this child was sent within the
     window (check recent `PremiumRequest`/`SentEmail`). Past the cap, record the request but skip the
     email and return `{status: "already_sent"}`.
  3. On send: `get_email_sender().send(session, child.parent_email, "premium_request",
     {child_username, context_label, benefits}, subject_id=child.id)`.
  4. Return `{status: "sent" | "already_sent" | "no_parent"}` for the sheet to render.
- **`GET /parent/premium-requests`** (parent-auth via `get_current_parent`; in `app/routers/parent.py`):
  returns recent **unresolved** requests for this parent's children (`child_username`, `context_kind`,
  `context_label`, `created_at`), parent-scoped by `parent_email` (IDOR-safe, mirrors `list_children`).
- **Resolve on grant:** in `webhook_service.handle_checkout_completed`, after the
  `set_premium(... value=True ...)` loop and before `session.commit()`, mark this parent's open
  `PremiumRequest`s `resolved_at = now`. (So no stale flags after subscribing.)
- **Email template `"premium_request"`** — "Penny — your child would love Premium": names the child +
  the content they hit + the benefits list, and routes the parent to **their dashboard/account**
  (no external-checkout link — Section 4). Added alongside the existing templates in `app/services/email.py`.
- **Parent dashboard** (`frontend/src/pages/ParentDashboard.tsx`): a compact **"Premium requested"**
  indicator above `SubscriptionCard` (e.g. "Ava asked to unlock *Investing Basics*"), fed by
  `GET /parent/premium-requests`. `SubscriptionCard` stays the subscribe entry.
- **Centralized tunables** `app/services/premium_config.py` — request cap/cooldown + canonical
  benefits list (used by the email); FE `premiumConfig.ts` mirrors the benefits copy so app + email agree.

**COPPA/safety:** only data is the child's username + content label, emailed to the **on-file**
`parent_email`; no new PII; no child payment; the cap prevents nagging.

---

## Section 3 — Wiring across every gated surface

**Backend — standardize the premium signal.** Enrich every premium `403` with a structured body
`{ detail, code: "premium_required", context: { kind, label } }` on: `/modules/{id}/lessons`,
`/levels/{id}/lessons`, the simulator premium-ticker block, and `/home-greeting`. List endpoints keep
their existing `locked`/`locked_reason`. No gating logic changes — only the response shape.

**Frontend — one interception point.** Extend `ApiError` (`src/api/client.ts`) to also capture the
response body's `code` and `context` (today it only keeps `status` + `detail`). Components that hit a
premium gate catch `ApiError` with `code === "premium_required"` and call
`usePremiumPaywall().open(context)`. Wire each surface:
- **Module tiles** (`locked`) → tap opens the paywall (replaces the dead dimmed tile).
- **Level cards** (`locked_reason: 'premium'`) → tap opens the paywall (replaces the toast).
- **Level-lessons page** → on `premium_required`, render the paywall sheet inline (replaces the static text).
- **Simulator** → blocked premium ticker opens the paywall; premium tickers carry `PremiumBadge`.
- **AI coach / home-greeting** → premium gate shows a premium state that opens the paywall.
- **Premium challenges** → `PremiumBadge` on the card; tap opens the paywall.

**Free/premium clarity (the "what's free" half):** premium is consistently badged; free content stays
clean/unmarked so the distinction reads at a glance. A short "Free vs Premium" line on `SubscriptionCard`
lists what each tier includes (from the shared config).

---

## Section 4 — Apple/Google constraints, edge cases, testing, scope

**Compliance (critical).** The child paywall and the parent email must **not** steer to an external
purchase (App Store 3.1.1): no price, no "subscribe on the web" link, no purchase button in the child
app or the email. 4B *informs* and *routes to the parent*; purchase stays the parent's existing
`SubscriptionCard` (web Stripe today; native pay = **4A**). On native, "Ask my grown-up" still emails
the parent, so iOS kids are never dead-ended and there's no IAP-bypassing UI → 4B ships on iOS now.

**Edge cases & safety**
- Frequency cap is enforced **server-side** (a child can't spam the parent); the sheet shows
  "we already told them today" past the cap.
- Open requests **auto-resolve** when premium is granted (webhook), so no stale "requested" flags.
- A child who already has premium never sees locks/paywall (live `is_premium`, unchanged).
- No new PII; no child payment; play-money economy untouched.

**Testing**
- *Backend*: `PremiumRequest` model + migration; `POST /premium/request` (records, sends one email,
  respects the cooldown cap, `no_parent`/`sent`/`already_sent` statuses); `GET /parent/premium-requests`
  (parent-scoped, IDOR-safe, excludes resolved); webhook resolves open requests on grant; the enriched
  `premium_required` 403 shape on each gate. Async tests (`loop_scope="session"`) + `client`/
  `admin_client`/`db_session` fixtures.
- *Frontend*: `PremiumPaywall` (benefits render, fires request, confirmation states) + `PremiumBadge`;
  `ApiError` `premium_required` interception; each wired surface; `vitest-axe` for the sheet + badge.
  Full `npm test`.

**Explicitly out of scope** (own sub-projects): real payments / native IAP — **4A**; subscription
nudges / upsell timing — **4C** (4B's child→parent request is a *direct* action, not a scheduled
nudge); per-lesson premium or tiered pricing — not planned.

**Promotion note:** built on `testing`; a new DB migration ships, so when promoted it runs per-env
(`testing` → `staging` → `production`) — and the production migration follows the **backup-first**
rule in `docs/deployment-environments.md`.
