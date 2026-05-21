# Compliance + Auth Completeness Design

## Goal

Close the auth-completeness gaps (email verification, password reset) and bring Invest-Ed into demonstrable compliance with the children's-privacy regime that applies to each user's jurisdiction. Jurisdiction is resolved dynamically from the user's `country_code`, mirroring the existing `consent_threshold(country_code)` pattern.

This is sub-project 1 of a larger programme (decomposed separately). It is intentionally scoped to compliance + auth. Tier/premium work, security audit, accessibility, and mobile are separate sub-projects.

## Motivation

The app already has a strong security baseline (Argon2, refresh-token rotation with DB revocation, account lockout, CSRF double-submit, security headers, timing-attack mitigation, soft-delete, audit logging, working parental-consent flow with Resend email). The remaining gaps are:

- No email verification — neither child nor parent email is ever proven.
- No password reset / forgot-password flow.
- No GDPR data export (subject-access request).
- No data-retention purge — soft-deleted rows persist indefinitely.
- No privacy notice/terms surfaced at signup; age is self-declared only.
- UK Age-Appropriate Design Code (AADC) net-new standards (high-privacy defaults, data minimisation, profiling-off-by-default, child-friendly notice, DPIA) not addressed.

## Locked Decisions

| Decision | Choice |
|---|---|
| Regulatory scope | Resolved dynamically by `country_code`: UK → UK AADC + UK GDPR; US → COPPA; EU → GDPR-K; HK → PDPO |
| Email verification | Parent email only, **gates** under-age (consent-required) accounts. Older teens/adults verify their own email (non-gating, capped state until verified) |
| Password reset | Age-split: consent-required child → reset routed to **parent** email; older teens/adults → standard self-service to own email |
| AADC depth | Implement **all** net-new standards (high-privacy defaults, child-friendly notice + terms, data minimisation, profiling-off-by-default, DPIA document) |
| Data retention | 30 days after `deleted_at`, then hard-purge PII. Configurable, default 30 |
| Data export | Parent (for consent-required kids, via parent dashboard) + self-service (older teens/adults, from settings). Machine-readable JSON |
| Architecture | **Approach A** — centralised compliance policy resolver; one tested source of truth |

## Architecture

### Approach A: Centralised Compliance Policy Resolver

A single module, `app/services/compliance.py`, exposes:

```python
@dataclass(frozen=True)
class CompliancePolicy:
    regime: Regime                       # UK_AADC | COPPA | EU_GDPRK | HK_PDPO
    consent_age: int                     # age below which parental consent is required
    requires_parental_consent: bool      # for this user (age vs consent_age)
    email_verification_target: str       # "parent" | "self"
    password_reset_mode: str             # "parent" | "self"
    data_retention_days: int             # default 30
    profiling_default_off: bool          # True for all regimes

def resolve_policy(country_code: str, dob: date, today: date) -> CompliancePolicy: ...
```

`Regime` is an enum. Jurisdiction → regime mapping and per-regime consent ages live as data inside this module:

| Regime | Countries | Consent age |
|---|---|---|
| UK_AADC | GB | 13 |
| COPPA | US | 13 |
| EU_GDPRK | IE, NL, DE, LU, SK, HR (16); other EU (13) | 13 or 16 |
| HK_PDPO | HK | 13 |
| Default | anything else | 13 |

`consent_service.consent_threshold()` and `needs_parental_consent()` become thin wrappers delegating to `resolve_policy()`, so existing callers and tests continue to pass unchanged. `age_in_years()` stays where it is and is reused.

**Why A:** rules are data, not behaviour; one tested API; trivially extensible; folds the existing `consent_threshold` idiom into the same place rather than scattering jurisdiction logic across routers.

## Components

### §1 Compliance Policy Core

- **Create** `app/services/compliance.py` — `Regime` enum, `CompliancePolicy` dataclass, `resolve_policy()`, internal `_REGIME_BY_COUNTRY` and `_CONSENT_AGE_BY_REGIME` tables.
- **Modify** `app/services/consent_service.py` — `consent_threshold()` / `needs_parental_consent()` delegate to `resolve_policy()`. Keep signatures identical.
- Single source of truth consulted by auth, consent, password-reset, and export code.

### §2 Email Verification (parent-gated)

- **Token:** new `OneTimeToken` purpose `verify_email`, JWT audience `verify_email`, expiry 24h (reuse `tokens.py` machinery).
- **Consent-required signup:** the existing consent email already proves the parent address — verifying the parent *is* the legal gate. No second email. `parent_consent_given_at` continues to be the activation gate. No change to that flow beyond noting parent-email-proven in the consent record.
- **Non-consent users (self target):** on registration, issue a `verify_email` token to the user's own email and send a new `verify_email` template. Account is `is_active=True` but `email_verified_at IS NULL`. Unverified state shows a frontend banner prompting verification and blocks changing the account email until verified; it is otherwise non-gating for login. (This is the only behavioural difference for unverified accounts — profiling-off is a global default per §5, not an unverified-specific cap.)
- **New column:** `users.email_verified_at` (datetime, nullable).
- **Endpoints:**
  - `GET /auth/verify-email?token=` — consume token, set `email_verified_at=now`, 410 on invalid/expired.
  - `POST /auth/verify-email/resend` — authenticated; rate-limit 3/hour; 202 always.
- **Email template:** `verify_email` (plain + HTML), same style as existing templates.

### §3 Password Reset (age-split)

- **Tokens:** new `OneTimeToken` purpose `password_reset`, audience `password_reset`, expiry 1h.
- **`POST /auth/forgot-password`** — body `{email}`. Always returns 202 (no account enumeration). Rate-limit 3/hour per IP. Look up active, non-deleted user by email. If found, `resolve_policy()` decides recipient:
  - `password_reset_mode == "parent"` → send to `user.parent_email` (fall back to no-op + 202 if absent).
  - `password_reset_mode == "self"` → send to `user.email`.
  - Email template `password_reset` (plain + HTML) with link `{app_base_url}/reset-password?token=`.
- **`POST /auth/reset-password`** — body `{token, new_password}`. Consume token atomically. Enforce existing password rules (12–128, letter+digit). On success: set new `password_hash`, **revoke all of the user's refresh tokens**, clear `failed_login_count`/`locked_until`. CSRF-exempt (pre-auth, token-protected), like `/auth/login`.
- Frontend: `/reset-password` page (token from query) + "Forgot password?" link on login.

### §4 Data Lifecycle

- **Retention purge:**
  - **Config:** `data_retention_days: int = 30` in `config.py`.
  - **Function:** `app/services/retention.py::purge_expired_accounts(session, today)` — for users where `deleted_at IS NOT NULL AND deleted_at < today - retention_days`: null/overwrite PII columns (`email`, `username`, `password_hash`, `dob`, `parent_email`, `topic_path`) with deterministic tombstone values, set a `purged_at` timestamp. Preserve the row + `audit_logs`/`sent_emails` minimal stubs for legal/audit (no PII).
  - **New column:** `users.purged_at` (datetime, nullable, indexed).
  - **Runner:** CLI entrypoint `python -m app.cli purge-accounts`; documented cron in `docs/compliance/operations.md`. No in-process scheduler (YAGNI; cron/k8s job is the deployment contract).
- **GDPR export:**
  - **`GET /users/me/export`** — authenticated. Allowed when policy is `self` reset mode (older teens/adults) OR explicitly for any owner of their own data. Returns JSON: profile, progress/XP, lesson completions, simulator portfolio + trades, consent history, sent-email metadata (templates + timestamps, not bodies). `Content-Disposition: attachment`.
  - **Parent export:** `GET /parent/children/{user_id}/export` — parent-session-authenticated, same JSON shape, for consent-required children.

### §5 AADC Net-New Standards (all)

- **High-privacy defaults:** new columns `users.profiling_enabled` (bool, default `False`), `users.marketing_opt_in` (bool, default `False`). Adaptive-AI / personalisation features must check `profiling_enabled` and degrade gracefully when off. No behavioural nudge patterns introduced. (Audit of existing nudge/streak mechanics for "detrimental use" is logged as backlog — streaks are retained as they are standard educational gamification, but documented in the DPIA.)
- **Child-friendly privacy notice + terms:** short, plain-language, age-appropriate copy. Shown at signup with an explicit, unticked acknowledgement control. Store `users.policy_version_accepted` (str) + `users.policy_accepted_at` (datetime). Versioned constant `PRIVACY_NOTICE_VERSION`. Re-prompt on version bump at next login.
- **Data minimisation:** make child `email` **optional** when `parent_email` is present (parent is the contactable/legal party). Consequence: **login identifier becomes username-or-email** — accounts registered without a child email log in with username + password. `RegisterRequest` rule: if the user is consent-required, child `email` is optional but `parent_email` is required; if not consent-required, the user's own `email` is required (needed for self-service verification and reset). Never require both a child email and parent email. `topic_path` is retained (the later personalisation sub-project consumes it) but stays optional and is never a required/dark-pattern field at signup. Document the full data inventory + lawful basis in the DPIA.
- **DPIA + privacy notice docs:** `docs/compliance/DPIA.md` (data inventory, lawful basis per regime, risks + mitigations, retention, children-specific risks) and `docs/compliance/privacy-notice.md` (the public child-friendly notice source of truth; frontend copy derives from it).

### §6 Compliance Test Accounts

- **Seed script** `app/seed/compliance_accounts.py` (idempotent, dev/test only, guarded by `environment != "production"`):
  - `pending-consent@test.invest-ed` — under-age (e.g. age 10, GB), `is_active=False`, consent token issued (printed to console).
  - `consented-child@test.invest-ed` — under-age, parent-approved, active.
  - `teen@test.invest-ed` — age 15 GB (≥ consent age, self target), `email_verified_at` null to exercise the verify flow.
  - `parent@test.invest-ed` — linked parent for the two child accounts.
- Free/premium **tier** test accounts are explicitly **out of scope here** — they belong to the later tier sub-project.

## Data Flow

1. **Register (under-age):** `resolve_policy` → `requires_parental_consent=True` → existing consent email (parent proof) → account inactive → parent approves → active. Unchanged except policy now comes from `compliance.py`.
2. **Register (teen/adult):** policy `self` → account active, `email_verified_at` null → `verify_email` sent → user clicks → verified.
3. **Forgot password:** email in → policy decides parent vs self recipient → token email → reset page → new password → all refresh tokens revoked.
4. **Deletion → purge:** parent erasure sets `deleted_at` → 30 days later cron `purge-accounts` overwrites PII, sets `purged_at`.
5. **Export:** owner (self) or parent (for child) requests → JSON attachment.

## Error Handling

- All token consume paths: 410 GONE on invalid/expired/reused (consistent with existing consent endpoints).
- `forgot-password`: always 202, never reveals account existence; absent `parent_email` in parent mode → silent no-op + 202.
- `reset-password`: 400 on weak password (existing validator messages); 410 on bad token.
- Purge: idempotent; running twice is safe (skips already-`purged_at` rows).
- Export: 403 if requester is not owner/linked-parent; 410 if account purged.

## Testing

- **Unit — policy resolver:** every regime × age boundary (e.g. GB age 12/13, IE age 15/16, US 12/13, HK 12/13, unknown country). Assert `requires_parental_consent`, `email_verification_target`, `password_reset_mode`, `consent_age`.
- **Unit — retention:** purge selects only `deleted_at < now-N`; PII overwritten; `purged_at` set; second run is no-op.
- **Integration — verify email:** teen registers → token issued → GET verifies → `email_verified_at` set; resend rate-limited; reused token 410.
- **Integration — password reset:** under-age → email goes to parent address; teen → own address; enumeration returns 202 both ways; reset revokes refresh tokens; weak password 400.
- **Integration — export:** self export shape; parent export for child; non-owner 403.
- **Regression:** existing consent + auth + security test suites stay green (wrappers preserve behaviour).

## Out of Scope (documented backlog)

- Stripe / payments (separate, deferred sub-project).
- Verifiable parental consent stronger than email (credit-card/ID) for strict COPPA — note as future option in DPIA.
- Cookie-consent banner / analytics consent (only needed if analytics added later).
- Security OWASP audit, accessibility, mobile, tier system — separate sub-projects.
- In-process scheduler for purge (cron/k8s job is the contract).

## File Map (indicative)

| File | Action |
|---|---|
| `app/services/compliance.py` | Create — resolver, policy, regime tables |
| `app/services/consent_service.py` | Modify — delegate to resolver |
| `app/services/retention.py` | Create — purge logic |
| `app/services/email.py` | Modify — `verify_email`, `password_reset` templates |
| `app/services/tokens.py` | Modify — new purposes/audiences |
| `app/routers/auth.py` | Modify — verify-email + forgot/reset endpoints |
| `app/routers/users.py` | Modify — `/users/me/export` |
| `app/routers/parent.py` | Modify — `/parent/children/{id}/export` |
| `app/models/user.py` | Modify — `email_verified_at`, `purged_at`, `profiling_enabled`, `marketing_opt_in`, `policy_version_accepted`, `policy_accepted_at` |
| `app/schemas/auth.py` | Modify — optional child email rule, policy acceptance field |
| `app/routers/auth.py` (login) | Modify — accept username **or** email as login identifier |
| `app/core/config.py` | Modify — `data_retention_days`, `PRIVACY_NOTICE_VERSION` |
| `app/cli.py` | Create — `purge-accounts` command |
| `app/seed/compliance_accounts.py` | Create — seed test accounts |
| `alembic/versions/*` | Create — migration for new columns |
| `docs/compliance/DPIA.md` | Create |
| `docs/compliance/privacy-notice.md` | Create |
| `docs/compliance/operations.md` | Create — cron/runbook |
| Frontend: signup notice/ack, `/reset-password`, verify banner, forgot link | Modify/Create |
| Tests across `tests/` | Create/Modify |
