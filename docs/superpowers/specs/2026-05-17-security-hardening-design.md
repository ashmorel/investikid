# Security Hardening Design (Sub-project 2)

## Goal

Run a systematic OWASP Top 10 security audit of Invest-Ed and fix all findings in application code and dependencies, then install an automated security gate in CI so regressions are caught. The LLM/AI attack surface is audited and documented here but its fixes are deferred to the later AI sub-project.

This is sub-project 2 of the larger programme. Sub-project 1 (Compliance + Auth) is shipped.

## Motivation

Invest-Ed processes children's PII and has parent/child trust boundaries, JWT/refresh-token sessions, a virtual-money simulator, and parent-managed account controls. A children's app carries elevated regulatory and reputational risk from security defects (broken access control, PII leakage, session flaws). A strong baseline already exists (Argon2, refresh-token rotation with DB revocation, account lockout, CSRF double-submit, security headers, timing-attack mitigation, rate limiting, soft-delete, audit logging) but it has never been systematically audited against OWASP Top 10, dependencies have never been CVE-scanned, and CI has no security tooling.

## Locked Decisions

| Decision | Choice |
|---|---|
| Audit surface | Backend app code + frontend app code + dependency CVEs + LLM surface (LLM = audit/document only) |
| LLM/AI security | Audit and document risks + recommended mitigations here; defer code fixes to the AI sub-project |
| Dependency CVEs | Fix **all** flagged deps — upgrade/pin to non-vulnerable versions, resolve breaking changes within this sub-project |
| CI tooling | Add a required CI security gate (bandit, pip-audit, npm audit) to the existing pipeline |
| Methodology | Approach A — OWASP-category audit → fix → CI gate, with a threat-model lens for prioritisation |
| Rigor | Audit + fix **all** non-LLM findings (no severity floor for app/dep fixes) |

## Architecture / Methodology

### Approach A: OWASP-category audit → fix → CI gate (with threat-model lens)

A single severity-rated **findings register** drives the work. The audit walks the OWASP Top 10 (2021) categories systematically for mechanical completeness, but prioritisation is risk-driven via a lightweight threat model so the highest-impact issues for *this* app (broken access control / IDOR on child & parent data, child-PII exposure, session integrity) are addressed first. Automated scanners serve a dual role: an **input** to the audit (surface mechanical issues fast) and the **durable CI gate** (catch regressions). Each fix lands with a regression test that proves the specific vulnerability is closed.

**Why A:** maps 1:1 to the user's "OWASP Top 10 + fix all" intent; auditable (every finding traceable in the register); the OWASP checklist guarantees mechanical coverage while the threat-model lens guarantees the children's-app-specific risks aren't drowned out by low-severity scanner noise; the CI gate makes the hardening durable rather than a one-off.

### Threat Model (preamble to the register)

- **Assets:** child PII (email, dob, username, parent_email, progress), parent PII & parent-session tokens, JWT access/refresh tokens, CSRF tokens, one-time tokens (consent/verify/reset), simulator virtual state, audit logs, LLM provider API keys.
- **Trust boundaries:** unauthenticated ↔ authenticated child; child ↔ parent (a child must not act as a parent; a parent must only reach their own children); app ↔ external LLM providers; app ↔ email provider.
- **Actors:** unauthenticated attacker; malicious/curious authenticated child; malicious/curious authenticated parent (IDOR across families); compromised dependency; network MITM (cookie/transport flags).
- **Highest-impact risks for this app (prioritise):** A01 Broken Access Control / IDOR on `/parent/*`, `/users/*`, simulator and content ownership; A02 Cryptographic/secret handling & cookie/transport flags; A07 auth/session integrity (token confusion, fixation, lockout bypass); A09 PII/secret leakage in logs and error responses.

## Components

### §1 Findings Register & Methodology

- **Create** `docs/security/audit-2026-05.md`: threat-model preamble; a findings table with columns — ID, OWASP category, title, severity (Critical/High/Medium/Low using a CVSS-style rubric documented in the file), location (`file:line` / dependency), description, fix status (Open/Fixed/Deferred/Accepted), fix commit, regression test.
- Severity rubric (explicit, no ambiguity): **Critical** = unauthenticated remote compromise or mass child-PII exposure; **High** = authenticated privilege escalation / cross-family IDOR / single-user PII exposure / auth bypass; **Medium** = security misconfig with limited blast radius, info leak requiring chained conditions; **Low** = defence-in-depth gaps, hardening nits.
- The register is the single source of truth; every audited area produces either a finding row or an explicit "reviewed — no finding" row so coverage is provable.

### §2 Manual Backend App-Code Audit + Fixes

OWASP-category walk of the FastAPI backend. Each category: enumerate the relevant code, record findings, fix, add regression test.

- **A01 Broken Access Control / IDOR (highest priority):** every endpoint under `app/routers/` that takes an id or returns user-scoped data — `parent.py` (all `/parent/children/{id}/*` incl. export/freeze/erasure), `users.py` (`/users/me*`, export), simulator routes, content/progress routes, consent/auth token endpoints. Verify each enforces ownership/authorisation (the `_get_owned_child` pattern) and that no endpoint trusts a client-supplied id without scoping to the authenticated principal. Verify child cannot reach parent-only endpoints and vice-versa.
- **A02 Cryptographic Failures:** cookie flags (`httponly`, `secure`, `samesite`) on all auth/CSRF cookies across environments; JWT signing/alg pinning (no `alg=none`/confusion); one-time-token entropy & expiry; secrets only from config/env, never logged or returned.
- **A03 Injection:** all DB access uses SQLAlchemy parameterised queries (grep for any raw SQL / string-built queries / `text()`); no `eval`/`exec`/unsafe deserialisation; path handling for any file/route param; JSON body size limits.
- **A04 Insecure Design / A05 Security Misconfiguration:** CORS config (origins not `*` with credentials), debug disabled in non-dev, generic error responses (no stack traces/internal detail to clients), security headers completeness incl. CSP, HSTS in prod, rate-limit coverage on all sensitive/auth endpoints, no default/seed creds reachable in prod (the compliance seed is already prod-guarded — verify).
- **A07 Identification & Auth Failures:** token type/audience enforcement (access vs refresh vs one-time), session fixation on login/privilege change, lockout cannot be bypassed or used for enumeration, password reset/verify token single-use & expiry (already built — re-verify under attack lens).
- **A08 Software/Data Integrity:** no untrusted deserialisation; CI/build inputs; one-time-token tampering resistance.
- **A09 Logging & Monitoring Failures:** confirm no passwords, password hashes, tokens, or PII written to logs or audit records; error handlers don't leak internals; auth-relevant events are audit-logged (login, reset, consent, erasure).
- **A10 SSRF:** any server-side outbound request taking a user-influenced URL (email links are app-generated — verify; LLM/provider URLs are config — verify not user-controlled).

Fixes committed per OWASP category (logical grouping), each with a regression test.

### §3 Frontend App-Code Audit + Fixes

- XSS sinks: React's unsanitised raw-HTML injection prop (the `dangerously`-prefixed inner-HTML setter), unsanitised URL/`href` construction, user content rendered without escaping, `target="_blank"` without `rel="noopener noreferrer"`.
- No tokens/secrets in `localStorage`/`sessionStorage` (auth is httpOnly-cookie based — verify nothing duplicates tokens client-side).
- CSP alignment with backend headers; no inline-script reliance that forces an unsafe CSP.
- Auth-state handling: protected routes truly gated; no sensitive data rendered pre-auth.
- Fixes + lightweight checks (and any that are statically detectable feed the CI gate).

### §4 Dependency Remediation

- Backend: `pip-audit` against `requirements.txt`. Frontend: `npm audit`.
- Remediate **every** finding: upgrade to a non-vulnerable version and pin it; where the safe version is a breaking major, perform the upgrade and fix the breakage **within this sub-project** (resolve, re-run full test suite green).
- Record before→after version and CVE id per dependency in the register.
- Re-run scanners post-upgrade to confirm zero remaining known vulns (or, if a vuln has no fixed version, document as an explicitly Accepted risk with rationale in the register — this is the only permitted non-fix and must be justified).

### §5 LLM Surface — Audit Only

- Document, in the register, risks for `tutor_service`, `chart_coach_service`, `ai_content_service`, `llm_client`: prompt injection (child input reaching model instructions), PII minimisation to providers (what child data is sent to Together/Groq/OpenAI), kid-safety of model output (unsafe/inappropriate content to a child), provider API-key handling, output handling (model output rendered to UI — XSS via model).
- For each: severity, recommended mitigation, and an explicit "Deferred to AI sub-project" status. **No code changes to the LLM surface in this sub-project** beyond anything that is *also* a generic app-code finding (e.g. a provider API key found in a log line is an A09 fix here; prompt-injection defence is deferred).

### §6 CI Security Gate

- Extend the existing CI workflow (`.github/workflows/`): add jobs/steps running **bandit** (Python SAST on `backend/app`), **pip-audit** (backend deps), **npm audit** (frontend deps, `--audit-level=high`).
- Gate policy: build **fails on High or Critical**; Medium/Low reported but non-blocking (so the gate is actionable, not noisy).
- False-positive handling: a documented, reviewed allowlist mechanism (bandit `# nosec` with a justification comment required; a pip-audit/npm audit ignore-list file with CVE id + rationale + review date). The allowlist lives in-repo and is itself reviewable.
- Document the gate + triage process in `docs/security/ci-security-gate.md`.

### §7 Testing

- Every Fixed finding has a regression test that **fails on the pre-fix code and passes after** — explicitly an attack-shaped test (e.g. parent A authenticated cannot GET parent B's child export → expect 404/403; tampered JWT alg rejected; reset token cannot be reused).
- The existing full suite (225 backend tests + frontend tsc/build) must remain green after every fix and after dependency upgrades.
- CI gate itself verified: a deliberately introduced trivial bandit-High (then reverted) confirms the gate blocks — described as a one-time manual verification step, not a committed test.

## Data Flow / Process

1. Build threat model + register skeleton (§1).
2. Run scanners → seed the register with mechanical findings (input role).
3. Manual OWASP walk backend (§2) → register rows.
4. Manual frontend audit (§3) → register rows.
5. Triage/prioritise by severity (threat-model lens: access-control / child-PII first).
6. Fix per category with regression tests (§2/§3), full suite green after each.
7. Dependency remediation (§4), full suite green after upgrades.
8. LLM surface documented as Deferred (§5).
9. Wire CI gate + allowlist + docs (§6).
10. Final pass: register has zero Open rows (every row Fixed / Deferred-LLM / Accepted-with-rationale); scanners clean at the gate threshold.

## Error Handling / Edge Cases

- A flagged dependency with no fixed version: allowed to be "Accepted" only with documented rationale + compensating control + review date in the register; must be called out, never silently skipped.
- A finding whose fix would require cross-sub-project scope (e.g. needs the future AI work): record as "Deferred" with the target sub-project named — only LLM-surface items qualify; app/dep items must be fixed here.
- A scanner false positive: must be allowlisted with written justification, not blanket-suppressed.

## Testing Strategy

Per-finding attack-regression tests (TDD-style: write the failing exploit test, apply the fix, test passes). Full backend suite + frontend tsc/build green as a gate after every fix and after dependency upgrades. CI gate manually verified to block on an injected High.

## Out of Scope

- LLM-specific code fixes (prompt-injection defence, kid-safe output filtering, PII-to-provider minimisation) — deferred to the AI sub-project; only documented here.
- Infrastructure / cloud / network / TLS-termination security (no infra in repo).
- Penetration testing of a deployed environment / DAST against a live host.
- Accessibility, premium/tier, mobile, content work (separate sub-projects).
- Bug-bounty / external audit engagement.

## File Map (indicative)

| File | Action |
|---|---|
| `docs/security/audit-2026-05.md` | Create — threat model + findings register |
| `docs/security/ci-security-gate.md` | Create — CI gate + triage/allowlist process |
| `backend/app/**` | Modify — per-finding fixes (A01–A10), scoped to actual findings |
| `frontend/src/**` | Modify — per-finding frontend fixes |
| `backend/requirements.txt` | Modify — pinned non-vulnerable versions |
| `frontend/package.json` / lockfile | Modify — remediated deps |
| `.github/workflows/*` | Modify — add bandit + pip-audit + npm audit gate |
| security allowlist files (bandit baseline / audit ignore) | Create if needed — reviewed, justified |
| `backend/tests/test_security*.py` (+ targeted test files) | Create/Modify — per-finding attack-regression tests |
| frontend security checks | Create/Modify as applicable |

The exact set of code files touched is determined by the audit findings; the plan will enumerate concrete tasks per OWASP category and per remediated dependency once the register exists.
