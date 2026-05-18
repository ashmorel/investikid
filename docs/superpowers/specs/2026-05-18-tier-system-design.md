# Tier System + Test Accounts Design (Sub-project 3)

## Goal

Make the free/premium tier distinction real, grantable (without Stripe), observable, and testable end-to-end, and seed dev/test accounts for each tier so every tier's behaviour can be exercised. This is the foundation the later "Premium content & AI engagement" sub-project (#4) builds on.

This is sub-project 3 of the programme. Sub-projects 1 (Compliance + Auth) and 2 (Security Hardening) are shipped.

## Motivation

`User.is_premium` exists (bool, default `False`, `nullable=False`) and already gates: the AI tutor message limit + model tier (`app/routers/ai.py` ×2), premium-only stock tickers (`app/routers/simulator.py:617`), premium content modules (`app/routers/content.py` filter), and premium gamification challenges (`app/routers/gamification.py`). But `is_premium` is **never set true anywhere**, and **all seeded modules/challenges are `is_premium=False`**, so the premium tier currently grants nothing observable and cannot be tested. There is no way to grant premium (Stripe deferred) and no per-tier test accounts.

## Locked Decisions

| Decision | Choice |
|---|---|
| Grant mechanism | Parent-dashboard toggle (parent = future payer) **+** an ops CLI grant. Seed accounts use the same writer. |
| Premium model | Per-child `is_premium` column kept, but **all reads/writes route through one entitlement service** so a future family/Stripe model swaps in behind the seam without touching call sites. |
| Demonstrability | Seed **1–2 sample premium modules + 1 premium challenge** (clearly labelled sample gating fixtures); real premium curriculum stays in sub-project #4. |
| Frontend | Tier badge **+ graceful locked-state affordances** (friendly "Premium" placeholder, **no checkout**) + the parent toggle. |
| Architecture | Approach A — a single `entitlements` service module as the seam. |

## Architecture

### Approach A: single entitlement service as the seam

`app/services/entitlements.py` is the one module that knows how premium is determined and changed. Today it reads/writes `User.is_premium`; a future family or Stripe model changes only this module's internals. Two functions:

- `is_premium(user: User) -> bool` — currently `return user.is_premium`. The single read seam.
- `set_premium(session, child: User, *, value: bool, actor: str) -> bool` — the single write seam. Idempotent (returns `False`/no-op if already at `value`); on change writes the column and an `AuditLog` row (event_type `premium_grant`/`premium_revoke`, the `actor`, the child `user_id`). Returns `True` if changed.

Every existing `user.is_premium` consumer is refactored to call `is_premium(user)`. The parent endpoint and the CLI both go through `set_premium` — there is exactly one code path that mutates entitlement, which is what a later subscription model will replace.

**Why A:** matches the locked decisions exactly (keep the column now, one helper seam); minimal churn (~5 call-site refactors, no schema change); the seam is independently unit-testable; avoids premature `Subscription` tables (YAGNI — Stripe/family are deferred).

## Components

### §1 Entitlement service (`app/services/entitlements.py`) — Create

- `is_premium(user) -> bool`: returns `user.is_premium`.
- `set_premium(session, child, *, value, actor) -> bool`: if `child.is_premium == value` → return `False` (no audit, no write). Else set `child.is_premium = value`, add `AuditLog(user_id=child.id, event_type="premium_grant" if value else "premium_revoke", ip_address=None)` (actor recorded in the audit row's available field — use the existing `AuditLog` shape; if it has no actor/metadata column, include the actor in `event_type` detail per the model's existing capability — confirm `AuditLog` columns at implementation time and use what exists without adding schema), `await session.flush()`, return `True`. Does **not** commit (caller owns the transaction, consistent with existing service conventions).
- Refactor these existing consumers to call `is_premium(current_user)` instead of reading `.is_premium` directly: `app/routers/ai.py` (both sites, ~L59 and ~L87), `app/routers/simulator.py:617`, `app/routers/content.py` (the module-list/detail premium filter, ~L50–75), `app/routers/gamification.py` (challenge `is_premium` filter, ~L75). Behaviour must be byte-identical (pure indirection) — verified by the existing suite staying green.

### §2 Parent premium toggle — `app/routers/parent.py` (Modify) + frontend

- New `POST /parent/children/{user_id}/premium`, body `{ "premium": bool }`. Auth: existing `get_current_parent` parent-session dependency. Ownership: `_get_owned_child(session, parent_email, user_id)` (same IDOR-safe pattern as freeze/erasure/export — a non-owning parent gets 404, never 200). If `child.deleted_at is not None` → 410 "Account deleted" (consistent with `freeze_child`/`export`). Rate-limited (reuse the limiter pattern used by other parent state-changing routes; if those aren't limited, match their convention — do not invent stricter limits than siblings). Calls `set_premium(session, child, value=payload.premium, actor=parent_email)`, commits, returns `{ "status": "ok", "premium": <value> }`.
- Schema: a small `PremiumToggleRequest` (pydantic, `premium: bool`) in the parent schemas module alongside `FreezeRequest`.
- Frontend: on the parent dashboard ChildCard, a control that reflects current state and toggles it — "Upgrade to Premium" when free, "Premium ✓ · Downgrade" when premium — calling the new endpoint via the existing `apiFetch` client (CSRF header auto-attached). Include short placeholder copy: "Billing isn't set up yet — this grants Premium for testing." No checkout/payment UI.

### §3 Ops CLI grant — `app/cli.py` (Modify)

- Extend the existing CLI (currently has `purge-accounts`) with `grant-premium <identifier> [--revoke]` where `<identifier>` matches a user by email **or** username (reuse the email-or-username lookup pattern from `auth.py` login). Resolves the user, calls `set_premium(session, user, value=(not revoke), actor="cli")`, commits, prints the result (`granted`/`revoked`/`no-op`). Exit 0 on success, 2 on bad args / user not found. No production guard needed (it's an explicit ops command), but it must not crash on unknown user — print a clear message + exit 2.

### §4 Demonstrable premium content — seed specs (Modify)

- In `app/seed/content.py`: mark **2** existing module specs `is_premium=True` (choose 2 thematically "advanced" modules, e.g. the crypto and the "advanced markets" style ones — pick by `order_index`/title at implementation, document which) OR add 2 clearly-named sample premium modules. Each must carry an inline comment: `# SAMPLE premium gating fixture — real premium curriculum is sub-project #4`.
- In `app/seed/gamification.py`: mark **1** challenge spec `is_premium=True` with the same comment.
- Verify the existing `content.py` premium filter behaviour: a free user requesting a premium module gets a clean denial (403 or filtered-out, whatever the current contract is) — **not** a 500. If the current filter only hides premium modules from the list but the detail endpoint 500s for a free user hitting a premium module by id, fix that one path to return 403 (in scope — it's the gate this sub-project must make demonstrable). Do not redesign the content API.

### §5 Tier test accounts — `app/seed/tier_accounts.py` (Create) + `app/seed/run.py` (Modify)

- New `seed_tier_accounts(session)` mirroring `seed_compliance_accounts`: guarded `if settings.environment == "production": return`; idempotent (skip if username exists); password `TestPassword1234!`; `@test.invest-ed` domain; each gets a `UserProgress` row (same as the compliance seed helper). Accounts:
  - `tier-parent` — parent identity (the `parent_email` owning `premium-child`); an adult/over-threshold self-account so it can also log in if useful. `parent_email` field on the children below = `tier-parent@test.invest-ed`.
  - `premium-child` — active child, `is_premium=True`, `parent_email=tier-parent@test.invest-ed`. Lets the §2 parent-toggle path be tested end-to-end (parent can downgrade then re-upgrade this child).
  - `free-child` — active child, `is_premium=False`, `parent_email=tier-parent@test.invest-ed`.
- Wire `seed_tier_accounts` into `app/seed/run.py` after the existing seeds (idempotent, prod-guarded — safe to run repeatedly). Do not duplicate the compliance accounts; this composes alongside them.
- Document the full test-account matrix (these + the compliance accounts + their tiers/passwords/purpose) in `app/seed/README` or a short `docs/testing/test-accounts.md` so a tester knows exactly which account exercises which tier/feature.

### §6 Frontend tier visibility

- Ensure the child profile/session payload (`GET /users/me`) exposes `is_premium`. If `UserProfile` already includes it, no change; if not, add `is_premium: bool` to the `UserProfile` pydantic schema (the route returns the ORM `User`, so exposing the field suffices — mirrors how `email_verified_at` was added in sub-project 1). Add `is_premium: boolean` to the frontend `Me` type.
- A small **tier badge** in the child Shell/profile area ("Free" / "Premium ✨") — unobtrusive, kid-friendly, matches existing Tailwind/shadcn styling.
- A reusable **locked-state affordance** component for premium-gated items: where premium modules/challenges appear to a free child, show them with a lock + friendly "Premium" label + one-line placeholder ("Ask a grown-up — Premium unlocks this. Billing coming soon.") and no navigation into the gated item. This must render gracefully (no console errors, no broken layout) and is the visible proof of the tier difference.
- The parent ChildCard premium toggle from §2.

### §7 Testing

- **Unit** (`tests/test_entitlements.py`, new): `is_premium` returns the column value; `set_premium` flips the flag + writes one `AuditLog` + returns `True`; calling `set_premium` with the current value is a no-op (`False`, no audit row).
- **Integration — parent toggle** (`tests/test_parent_dashboard.py`, append): owning parent can upgrade then downgrade their child (state + audit assertions); a *non-owning* parent gets 404 (IDOR check, mirrors existing parent-route tests); deleted child → 410; response shape `{status, premium}`.
- **Integration — CLI** (`tests/test_*` for cli, append/new mirroring `test_retention`): `grant-premium` by username and by email flips the flag; `--revoke` clears it; unknown identifier → exit 2.
- **Integration — content gate**: a `free-child`-equivalent user is denied a premium module (clean 403/hidden, not 500); a premium user is allowed. Reuse existing content test fixtures.
- **Seed**: `seed_tier_accounts` idempotent (run twice → exactly 3 accounts), prod-guarded (no-op when `environment == "production"`).
- **Regression**: full backend suite stays green (the ~5 call-site refactors are pure indirection — any failure means the refactor changed behaviour and must be fixed, not the test loosened). Frontend `tsc --noEmit` + `build` green; the locked-state component renders for a free user.

## Data Flow

1. Parent opens dashboard → ChildCard shows each child's tier (from the children list payload — extend the existing parent children response with `is_premium` if not present).
2. Parent clicks Upgrade → `POST /parent/children/{id}/premium {premium:true}` → ownership-checked → `set_premium(actor=parent_email)` → audit row → committed → UI reflects "Premium ✓".
3. Premium child logs in → `/users/me` shows `is_premium:true` → badge "Premium ✨", premium modules/challenges accessible, higher tutor limit, premium stock tickers, premium LLM tier (all via `is_premium()` seam).
4. Free child sees premium modules as locked-state affordances; hitting one by URL → clean 403 + friendly UI, never a crash.
5. Ops runs `python -m app.cli grant-premium someone@test.invest-ed` → same `set_premium` path → audited.

## Error Handling / Edge Cases

- `set_premium` idempotent: no audit/no write when value unchanged (prevents audit spam from a double-click).
- Parent toggling a deleted child → 410; a frozen (`is_active=False`) child → still allowed (premium is orthogonal to active state; document this — a parent may pre-provision premium; no security impact).
- Non-owning parent → 404 (never reveal another family's child).
- Free user hitting a premium module by id → 403 with a generic body (no internal detail), frontend shows the locked state, never a 500.
- CLI unknown user → stderr message + exit 2; never a traceback.
- All entitlement changes (parent or CLI) produce an `AuditLog` row with the actor, so grants are traceable (important for a children's app + future billing reconciliation).

## Out of Scope

- Stripe / checkout / billing / subscription lifecycle (deferred sub-project).
- Family / multi-child shared entitlement (the seam permits it later; not built now).
- Real premium curriculum / content depth and the deferred **LLM-03** kid-safe-output moderation — both sub-project #4.
- Accessibility pass and mobile-first (separate sub-projects 5/6).

## File Map (indicative)

| File | Action |
|---|---|
| `backend/app/services/entitlements.py` | Create — `is_premium`, `set_premium` |
| `backend/app/routers/ai.py`, `simulator.py`, `content.py`, `gamification.py` | Modify — route reads through `is_premium()` |
| `backend/app/routers/parent.py` | Modify — `POST /parent/children/{id}/premium` |
| `backend/app/schemas/parent*.py` | Modify — `PremiumToggleRequest` |
| `backend/app/cli.py` | Modify — `grant-premium` command |
| `backend/app/seed/content.py`, `gamification.py` | Modify — sample premium fixtures |
| `backend/app/seed/tier_accounts.py` | Create — tier test accounts |
| `backend/app/seed/run.py` | Modify — wire tier-account seed |
| `backend/app/schemas/user.py` | Modify — expose `is_premium` on `UserProfile` if absent |
| `backend/app/routers/parent.py` (children list) | Modify — include `is_premium` per child if absent |
| `docs/testing/test-accounts.md` | Create — test-account/tier matrix |
| `frontend/src/api/auth.ts` (Me type) | Modify — `is_premium` |
| `frontend/src/components/child/*` | Modify/Create — tier badge + locked-state affordance |
| `frontend/src/pages/ParentDashboard*.tsx` / ChildCard | Modify — premium toggle |
| `backend/tests/test_entitlements.py` + appends to parent/cli/content/seed tests | Create/Modify |

The exact modules chosen as sample-premium and the precise frontend component placement are settled in the implementation plan against the real code.
