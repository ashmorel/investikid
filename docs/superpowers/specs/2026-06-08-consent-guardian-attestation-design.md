# Parent/Guardian 18+ Attestation (Fix #3) — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`

## Background

An audit of the existing age-of-consent flow found it **already compliant** — no bug to fix:
- `app/schemas/auth.py::validate_dob` enforces: dob in the past, **age ≥ 8**, age ≤ 120.
- `app/services/compliance.py::resolve_policy` selects the regime per country (UK AADC, US COPPA, EU GDPR-K, HK, default) and consent age (**13**, or **16** for EU-16 countries).
- `app/routers/auth.py::register`: below the consent age, a `parent_email` is required, the account is created **inactive** (`is_active = not needs_consent`), and a consent email is sent.
- `app/routers/consent.py::decide_consent`: the parent approves (sets `parent_consent_given_at`, `is_active = True`) or declines (`consent_declined_at`).

**Decision:** keep the minimum-age floor at **8** (younger children may use the app **with** parental consent). The one improvement is a **parent/guardian adult attestation** at the approval step, which also mitigates the residual gap that Google/Apple OAuth cannot verify the account-holder is an adult.

## Goal

At the consent-approval step, the parent must explicitly confirm they are the child's parent/legal guardian and over 18 before approval succeeds. Record the attestation timestamp for audit.

## Scope

- **In:** an attestation flag required on `approve`; a recorded `guardian_attested_at`; a checkbox gating the Approve button on the consent page.
- **Out:** changing the minimum age floor; changes to the OAuth flow itself; any change to the decline path; re-attestation on future logins.

## Section 1 — Backend

**Migration** (hand-written, chained; run `alembic heads` first, `down_revision` = current single head):
- Add nullable column `guardian_attested_at` to `users`: `sa.Column("guardian_attested_at", sa.DateTime(timezone=True), nullable=True)`. Downgrade drops it.

**Model** (`app/models/user.py`):
- Add `guardian_attested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)` (mirroring the other nullable timestamp columns like `parent_consent_given_at`).

**Schema** (`app/schemas/consent.py`):
- `ConsentDecision` gains `attest_guardian: bool = False`.

**Endpoint** (`app/routers/consent.py::decide_consent`):
- When `payload.decision == "approve"`: if `payload.attest_guardian is not True`, raise `HTTPException(400, "Guardian attestation required")` **before** mutating the user. On success set both `user.parent_consent_given_at = now` and `user.guardian_attested_at = now`, `user.is_active = True`.
- When `payload.decision == "decline"`: unchanged (attestation not required/ignored).
- The one-time consent token is consumed at the top of the handler. To avoid burning the token on a 400 (which would block a legitimate retry), perform the `attest_guardian` validation **before** `consume_one_time_token`, or re-issue is not required because the frontend gates Approve behind the checkbox so a missing attestation can only happen via a direct API call. **Chosen:** validate `attest_guardian` first (before consuming the token) so a malformed approve doesn't consume the link.

## Section 2 — Frontend

**API client** (`src/api/consent.ts`):
- `decide(token, decision, attestGuardian?: boolean)` → POST body includes `attest_guardian` (default omitted/false for decline).

**Consent page** (`src/pages/ConsentVerify.tsx`):
- Add a checkbox above the buttons, label: *"I confirm I am {child.username}'s parent or legal guardian and am over 18."*
- **Approve** button is `disabled` until the checkbox is checked (and while the mutation is pending). `decide.mutate` for approve passes `attestGuardian: true`.
- **Decline** button is unaffected (always enabled).
- Accessibility: real `<label>` associated with the checkbox (`htmlFor`/`id`), keyboard-operable, touch target ≥16px, no `maximum-scale` regressions. Use the existing shadcn `Checkbox` if present, else a native `<input type="checkbox">` styled consistently.

## Section 3 — Testing

**Backend pytest** (async, `loop_scope="session"`, `db_session`/`client`; reuse the consent-token test helpers in the existing consent tests):
- approve with `attest_guardian: false` (or omitted) → **400**, user stays inactive, token not consumed (still usable).
- approve with `attest_guardian: true` → **200**, `parent_consent_given_at` and `guardian_attested_at` both set, `is_active = True`.
- decline (no attestation) → **200**, `consent_declined_at` set, `is_active = False`.

**Frontend vitest + vitest-axe** (`ConsentVerify`):
- Approve disabled until the checkbox is checked; checking enables it; clicking Approve calls `decide` with `attestGuardian: true`.
- Decline works without the checkbox.
- No axe violations.

**Verify:** backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. The consent page is a web/parent surface (not in the child iOS shell), but it is part of the web build — no `cap sync` needed.

## Out of scope / notes

No change to the minimum age (8), the OAuth flow, or the decline path. The attestation is captured once at consent approval; it is not re-prompted. `guardian_attested_at` is for audit/compliance evidence only and drives no other behaviour.
