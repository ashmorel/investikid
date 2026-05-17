# Data Protection Impact Assessment (DPIA)

**Product:** Invest-Ed  
**Version:** 1.0  
**Date:** 2026-05-16  
**Privacy Notice Version:** 2026-05-16  
**Author:** Engineering & Compliance  
**Review Cycle:** Annual or on material change

---

## 1. Scope

Invest-Ed is a financial literacy education platform aimed primarily at young learners aged 8 and above, accessible via web browser. The platform delivers structured lessons on personal finance, investments, and economic concepts, with gamified progress mechanics including experience points (XP), levels, streaks, and virtual coins.

Because the platform explicitly targets children and processes personal data of minors, it falls within the scope of heightened child data protection regulation across its target markets. Jurisdiction is resolved on a per-user basis at registration time using `app/services/compliance.py::resolve_policy(country_code, dob, today)`, which maps the combination of a user's declared country code and date of birth to one of the following regulatory regimes:

- **UK_AADC** — UK Age Appropriate Design Code (Children's Code) + UK GDPR, applied when the user's country code is `GB` and the user is under 18.
- **COPPA** — US Children's Online Privacy Protection Act, applied when the user's country code is `US` and the user is under 13.
- **EU_GDPRK** — EU GDPR child-specific provisions, applied to users in EU member states. The age of digital consent varies: it is 16 in Ireland (IE), Netherlands (NL), Germany (DE), Luxembourg (LU), Slovakia (SK), and Croatia (HR); it is 13 in all other EU member states.
- **HK_PDPO** — Hong Kong Personal Data (Privacy) Ordinance, applied when the user's country code is `HK`.
- **DEFAULT** — General data minimisation and privacy-by-default posture for all other jurisdictions. Consent age is 13.

All processing described in this DPIA applies across all regimes except where a regime-specific note is given.

---

## 2. Data Inventory

The following table enumerates every column in the `users` table (defined in `app/models/user.py`), its processing purpose, the applicable lawful basis, and its retention treatment.

| Column | Purpose | Lawful Basis | Retention |
|---|---|---|---|
| `id` (UUID) | Primary key; internal record linkage | Necessary for contract / legitimate interest (service delivery) | Retained permanently as an opaque identifier even after purge; no PII |
| `email` | Login credential; account communications (nullable — children may omit) | Consent (for marketing); contract (for account access) | Overwritten to `NULL` on purge |
| `username` | Login credential; display name (always required) | Contract | Overwritten on purge |
| `password_hash` | Authentication (Argon2id hash; not raw password) | Contract | Overwritten on purge |
| `dob` | Age-gate enforcement; regime selection; aggregate analytics | Legitimate interest (child safety, legal compliance) | Retained after purge — non-identifying in isolation; required for age-gate audit trail |
| `country_code` | Jurisdiction resolution; regime selection; currency default | Legitimate interest (legal compliance) | Retained after purge — non-identifying in isolation |
| `currency_code` | Display currency for financial education content | Contract | Retained post-purge (non-identifying) — kept for aggregate analytics |
| `topic_path` | Personalised learning path (chosen or inferred onboarding topic) | Consent (profiling disabled by default; user opts in) | Overwritten on purge |
| `parent_email` | Parental consent flow for child accounts | Consent (parental); legitimate interest (child safety) | Overwritten on purge |
| `email_verified_at` | Tracks whether email address has been verified | Contract | Retained post-purge (non-identifying) — verification-status audit trail; not a direct identifier once email itself is removed |
| `purged_at` | Audit timestamp of PII overwrite | Legal obligation (demonstrable erasure) | Retained permanently |
| `is_active` | Account status; controls login and content access | Contract | Retained — operational field |
| `failed_login_count` | Account lockout (5 failures / 15 min window) | Legitimate interest (security) | Reset on successful login; cleared on purge |
| `locked_until` | Lockout expiry timestamp | Legitimate interest (security) | Cleared on purge |
| `profiling_enabled` | Controls whether behavioural profile is built for recommendations | Consent (explicit opt-in required; default false) | Retained — consent record |
| `marketing_opt_in` | Controls marketing communications | Consent (explicit opt-in required; default false) | Retained — consent record |
| `policy_version_accepted` | Version string of privacy notice accepted at registration | Legal obligation (GDPR Art. 7 — demonstrable consent) | Retained — consent audit record |
| `policy_accepted_at` | Timestamp of policy acceptance | Legal obligation | Retained — consent audit record |
| `parent_consent_given_at` | Timestamp of parental consent for child account activation | Legal obligation (parental consent regimes) | Retained — consent audit record |
| `consent_declined_at` | Timestamp when user declined consent (pre-activation) | Legitimate interest (consent management audit) | Retained — consent audit record |
| `deletion_requested_at` | Timestamp of erasure request (right to erasure trigger) | Legal obligation | Retained — erasure audit record |
| `deleted_at` | Timestamp of soft-delete (account deactivated, pending purge) | Legal obligation | Retained — erasure audit record |
| `is_premium` | Subscription tier flag | Contract | Cleared on purge |

---

## 3. Lawful Basis Per Regime

### 3.1 UK — AADC + UK GDPR

The UK Children's Code (Age Appropriate Design Code) applies to information society services likely to be accessed by under-18s. Invest-Ed is explicitly designed for children, so the Code applies in full.

**Parental consent for under-13s:** UK GDPR Article 8 sets the UK age of digital consent at 13. Users whose resolved age (from `dob` and `country_code = GB`) is below 13 must provide a parent email at registration. The account is created in an inactive state (`is_active = False`) with no personal email collected from the child. A consent invitation is sent to the parent email. The account activates and `parent_consent_given_at` is set only after the parent follows the consent link. Until activation the child has no access to the platform.

**Legitimate interest for core education:** Delivery of lesson content, progress tracking (XP, level, streak), and account security are processed under legitimate interest. These are necessary for the service the child or parent has requested and pose no material risk — the data is not shared with third parties, and the educational purpose is clearly in the child's interest.

**Data minimisation and child-email-optional:** Under the Children's Code, collection must be limited to what is strictly necessary. Child accounts under 13 do not require an email address (`email` is nullable). The child logs in with username and password only. This reduces the identifiability of the child's data and limits the attack surface.

**High-privacy defaults:** `profiling_enabled` defaults to `false` and `marketing_opt_in` defaults to `false` for all users. Under the Children's Code, the highest privacy settings must be the default. Personalised recommendations are gated on `profiling_enabled = true`, which requires an explicit opt-in action by the user (or their parent for under-13s). Marketing is never sent to users without explicit opt-in, and is never targeted at under-13s regardless of opt-in status.

### 3.2 COPPA — US

COPPA applies to online services directed at children under 13, or where the operator has actual knowledge that a user is under 13.

**Parental consent for under-13s:** COPPA requires verifiable parental consent before collecting, using, or disclosing personal information from children under 13. Invest-Ed implements an email-based parental consent gate: an email is sent to the provided `parent_email` and the account activates only when the parent clicks through. This mechanism is materially weaker than COPPA's preferred methods of verifiable consent (credit card charge, signed consent form, video call). See Residual Risks §5 for details.

**No behavioural advertising:** `marketing_opt_in` is `false` by default and under-13 US accounts are excluded from any marketing regardless of opt-in status.

### 3.3 EU GDPR-K — EU Member States

GDPR Article 8 allows member states to set the age of digital consent between 13 and 16. The `resolve_policy` function maps country codes to the correct threshold: 16 for IE, NL, DE, LU, SK, and HR; 13 for all other EU member states. Users below the applicable threshold in their country follow the same parental-consent gate as described under UK_AADC above.

**Data subject rights:** GDPR provides rights of access, rectification, erasure, restriction, portability, and objection. These are implemented as described in §6 (Subject Rights) below.

### 3.4 HK PDPO — Hong Kong

The Personal Data (Privacy) Ordinance establishes six Data Protection Principles. Invest-Ed's processing is designed to comply with:

- **DPP1 (Collection):** Data collected only for a directly related lawful purpose; notified to users at collection via the privacy notice.
- **DPP2 (Accuracy):** Users may correct their data via profile PATCH endpoints.
- **DPP3 (Use):** Data used only for the purpose for which it was collected; no sale or sharing with third parties.
- **DPP4 (Security):** Argon2id password hashing, JWT refresh-token rotation with DB revocation, account lockout, CSRF double-submit cookies, security headers.
- **DPP5 (Openness):** Privacy notice published at `/docs/compliance/privacy-notice.md` and linked from the signup flow.
- **DPP6 (Access & Correction):** Export and rectification endpoints as described in §6.

---

## 4. Children-Specific Risks and Mitigations

### 4.1 Self-Declared Age

**Risk:** A child could declare an incorrect date of birth to bypass the parental consent gate and register as an older user, gaining access without parental knowledge.

**Mitigations:**
- A parent email is required for all registrations where the provided date of birth puts the user below the applicable consent age. This creates a functional barrier even if age is mis-declared, because the account cannot activate without parental action.
- DOB plausibility is validated server-side: the declared age must fall between 8 and 120 years. Values outside this range are rejected at registration.
- Age-split flows are applied at the resolved age boundary. The registration path for under-age users is structurally different from the adult path — child accounts are created in an inactive state and cannot access the platform content until parental consent is confirmed.
- Fraudulent age declaration by a minor attempting to self-register as an adult would constitute misuse of the service; this is noted in the terms of service.

### 4.2 Profiling and Recommendations

**Risk:** Behavioural profiling of children, even for educational personalisation, carries risks including nudging, undue influence on financial attitudes, and collection of more data than necessary.

**Mitigations:**
- `profiling_enabled` defaults to `false` for all accounts. Recommendation features that depend on behavioural data are gated on this flag and are never displayed or called unless the user has explicitly opted in.
- For under-13 accounts, enabling profiling requires parental action. The consent flow is distinct from the general account activation flow.
- The data used for recommendations is restricted to in-app progress and topic preferences (XP, level, lesson completion, `topic_path`). No third-party tracking, fingerprinting, or cross-site data is used.

### 4.3 Gamification Mechanics

**Risk:** Streak counters, XP, and virtual coins are gamification mechanisms that could constitute "nudge techniques" or engagement maximisation contrary to children's best interests under the UK Children's Code.

**Justification and mitigations:** Streaks (`streak_count`), experience points (`xp`), levels (`level`), and virtual coins (`virtual_coins`) are retained as core mechanics because they serve a demonstrable educational purpose: they reward consistent engagement with learning material, not arbitrary platform time. There is no social comparison leaderboard, no monetisation of virtual coins (they cannot be converted to real currency or used for in-app purchases beyond cosmetic rewards), no push-notification pressure to maintain streaks, and no anxiety-inducing streak-loss penalty. The mechanics are reviewed annually against the Children's Code guidance on age-appropriate design to ensure they remain proportionate and in the child's interest.

### 4.4 Over-Collection

**Risk:** Collecting more data than necessary increases risk to children in the event of a breach and may constitute a GDPR/Children's Code violation.

**Mitigations:**
- Email is optional for child accounts. Children under the consent age log in with username and password only, and no email address is collected from the child themselves.
- Username-or-email login is supported so that a child account created without an email can still authenticate.
- `topic_path` is set at onboarding and used solely for content routing. It is treated as potentially sensitive (it may imply household financial circumstances) and is overwritten on purge.

---

## 5. Retention and Erasure

### 5.1 Retention Schedule

Invest-Ed implements a two-phase erasure process:

**Soft delete:** When a user requests erasure (right to erasure / right to be forgotten), or when an account is administratively closed, `deleted_at` is set to the current timestamp and `is_active` is set to `false`. The account is immediately inaccessible for login and all user-facing data access. The `deletion_requested_at` timestamp is also set if the deletion was initiated by a subject rights request.

**Hard purge (PII overwrite):** After `settings.data_retention_days` days (default: 30 days) following `deleted_at`, the account is eligible for purging. The purge is executed by `app/services/retention.py::purge_expired_accounts`, triggered via `python -m app.cli purge-accounts`. The purge process overwrites the following fields with anonymised values: `email`, `username`, `password_hash`, `parent_email`, `topic_path`. The `purged_at` timestamp is set on completion.

**Fields retained after purge:** `dob`, `country_code`, `currency_code`, and `email_verified_at` are retained post-purge. These values are not personally identifying in isolation — once the direct identifiers (`email`, `username`, `password_hash`, `parent_email`, `topic_path`) are removed, none of these fields can be linked to a natural person. They are retained to support: (a) age-gate audit trails demonstrating that underage users were handled correctly; (b) aggregate demographic and analytics purposes computed without joining to any identifier; (c) verification-status audit trail (`email_verified_at` is not a direct identifier once the email address itself is removed). This retention is deliberate and was approved during DPIA review.

**Idempotency:** The purge operation is idempotent. Running it multiple times against the same account produces the same result. Accounts already marked `purged_at IS NOT NULL` are skipped.

### 5.2 Parent Erasure

A parent who provided parental consent for a child account may request erasure of the child's account via the parent erasure endpoint. This triggers the soft-delete flow and queues the account for purge.

---

## 6. Subject Rights

| Right | Implementation |
|---|---|
| **Access / portability** | `GET /users/me/export` — authenticated user exports their own data as JSON. `GET /parent/children/{id}/export` — parent exports a linked child account. Response generated by `app/services/export_service.py::build_user_export`. Includes: profile fields, lesson progress, consent timestamps, sent emails addressed to the user or parent email. Excludes: `password_hash`, raw email body text. |
| **Rectification** | `PATCH /users/me` — authenticated user updates profile fields. Parent endpoint available for child account fields. |
| **Erasure** | Parent or adult user submits erasure request. Account soft-deleted immediately; PII purged after `data_retention_days`. Confirmation sent to registered email or parent email. |
| **Restriction** | Account can be set to inactive (`is_active = false`) on request, suspending processing without erasure. |
| **Objection to profiling** | `profiling_enabled` can be set to `false` at any time via profile PATCH. This immediately gates off all recommendation processing. |
| **Withdraw consent** | Parent may revoke parental consent; child account set inactive and queued for erasure on parental request. Marketing opt-in may be withdrawn at any time. |

---

## 7. Security Posture

The following security controls are implemented as of the current codebase baseline. They are relevant to the DPIA because the adequacy of technical security measures is a factor in the Art. 25 / Art. 32 GDPR analysis, and because the Children's Code requires that security is appropriate to the risk to children.

- **Password storage:** Argon2id hashing via `app/core/security.py::hash_password`. Argon2id is the current best-practice algorithm for password hashing (winner of the Password Hashing Competition).
- **Authentication tokens:** JWT access tokens with short expiry (15 minutes by default). Refresh tokens use rotation with database-level revocation (`refresh_tokens` table; `revoked_at` field). A compromised refresh token is invalidated on the next rotation event.
- **Account lockout:** 5 consecutive failed login attempts trigger a 15-minute lockout (`locked_until`). This mitigates brute-force and credential-stuffing attacks, which are of heightened concern for child accounts.
- **CSRF protection:** Double-submit cookie pattern. Stateful CSRF tokens are not required with this pattern; the cookie and header value are compared server-side on all mutating requests.
- **Security headers:** Standard HTTP security headers (HSTS, X-Content-Type-Options, X-Frame-Options, Content-Security-Policy) are set on all responses.
- **Timing-attack mitigation:** `app/core/security.py::dummy_verify` runs a full Argon2id verification against a pre-computed dummy hash on the "user not found" login path, equalising response time between "no such user" and "wrong password" outcomes. This prevents username enumeration via timing.

---

## 8. Residual Risks and Backlog

The following risks are known at the time of this DPIA. They are recorded as residual risks requiring future mitigation.

### Risk 1: Shared-Parent-Email Cross-Child Export Exposure (HIGH PRIORITY)

**Description:** `app/services/export_service.py::build_user_export` filters `SentEmail` records by `to_email == user.email OR to_email == user.parent_email`. Where two or more child accounts share the same `parent_email` (for example, siblings in the same household), a data export requested for one child may include `SentEmail` rows that were generated in relation to a sibling, because those sibling-related emails are also addressed to the shared parent email address.

**Current state:** There is no `SentEmail.subject_id` foreign key to identify which user a given sent email relates to. Filtering is address-based only.

**Planned mitigation:** Add a `subject_id` foreign key to the `SentEmail` model, referencing `users.id`. Filter the export query by `SentEmail.subject_id == user.id` in addition to (or instead of) the address-based filter. This is recorded as a future task and must be completed before the platform is made available in jurisdictions where sibling accounts are anticipated at scale.

**Status: Resolved in security sub-project — `SentEmail.subject_id` added; export scoped by `subject_id`. (2026-05-17)**

~~Residual risk until mitigated: A parent who requests a data export for Child A may receive emails that relate to Child B. While the data is disclosed to the parent (who has consent rights over both children), it is a correctness and minimisation failure. Under GDPR it constitutes sharing more data than requested. Severity: Medium. Likelihood: Low (requires multiple children with same parent email). Priority: High.~~

### Risk 2: Email-Based Parental Consent Weaker than COPPA Verifiable Consent

**Description:** COPPA regulations require "verifiable parental consent" — that the operator has made reasonable efforts to ensure that the consenting party is actually the parent or legal guardian. Email-click consent does not satisfy the COPPA standard of verifiable consent because there is no verification that the email recipient is an adult, let alone the child's parent or guardian.

**Current state:** Parental consent is implemented via an email sent to the `parent_email` provided at registration, with an activation link. This is sufficient for UK GDPR and EU GDPR-K (which do not specify the mechanism of parental consent), but is weaker than the COPPA requirement.

**Planned mitigation (candidate):** Supplement email consent with an age-verification step for the parent (e.g., credit card microcharge, digital ID verification, or callback verification). This is deferred pending product and commercial decisions. Until implemented, the platform should not be marketed directly at US audiences under 13.

**Residual risk until mitigated:** COPPA non-compliance risk for US under-13 users. Severity: High. Likelihood: Low (not currently marketed to US children). Priority: Medium.

### Risk 3: Cookie and Analytics Consent Scope

**Description:** If analytics or advertising cookies are added to the platform in future, a separate consent mechanism will be required under UK PECR / EU ePrivacy Directive. The current implementation has no analytics or third-party cookies and therefore no cookie consent banner is shown.

**Current state:** No third-party analytics or advertising. No cookies beyond the session/auth cookie required for service operation.

**Planned mitigation:** If analytics are added, implement a consent banner with genuine choice (accept / decline / manage), with decline as the default state. Do not use dark patterns. Update this DPIA.

**Residual risk until mitigated:** None currently. Residual risk is conditional on future product decisions.
