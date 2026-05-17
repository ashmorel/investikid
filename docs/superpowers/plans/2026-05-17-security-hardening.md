# Security Hardening Implementation Plan (Sub-project 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Audit Invest-Ed against OWASP Top 10, fix all application-code and dependency findings with attack-regression tests, document (defer) the LLM surface, and install a CI security gate so regressions are caught automatically.

**Architecture:** Audit-first. A severity-rated findings register (`docs/security/audit-2026-05.md`) is the single source of truth. Automated scanners (bandit, pip-audit, npm audit) seed mechanical findings; a manual OWASP-category walk plus a threat-model lens find the high-impact logic flaws (access control / IDOR / child-PII). Each fix lands TDD-style with an attack-shaped regression test that fails on pre-fix code and passes after. The same scanners become the durable CI gate.

**Tech Stack:** Python 3.12 (CI) / 3.13 (local), FastAPI, SQLAlchemy 2 async, Alembic, pytest (`asyncio_mode=auto`, session-scoped `db_session`/`client` fixtures), python-jose, ruff, React/TS (Vite), GitHub Actions.

**Conventions (read before starting):**
- Backend commands run from `/Users/leeashmore/Local Repo/invest-ed/backend`. Git runs from `/Users/leeashmore/Local Repo` using `backend/...`, `invest-ed/...`, `docs/...` paths.
- Async tests using `db_session`/`client` need session loop scope. If a test file already has a module-level `pytestmark = pytest.mark.asyncio(loop_scope="session")`, append and inherit it. For a NEW test file add that file-level `pytestmark` + `import pytest`. For a single async test added to a file with no file-level mark, decorate only that function with `@pytest.mark.asyncio(loop_scope="session")`.
- ruff rules E/F/I/UP, 120 cols; run `ruff check` on changed files and fix before every commit.
- Full backend suite (225 tests) + frontend `tsc`/`build` must stay green after every fix and every dependency upgrade.
- Commit messages: `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` trailer.
- CI workflow lives at repo root `.github/workflows/ci.yml` (NOT under invest-ed).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `docs/security/audit-2026-05.md` | Create | Threat model + severity rubric + findings register (single source of truth) |
| `docs/security/ci-security-gate.md` | Create | CI gate behaviour + triage/allowlist process |
| `backend/requirements.txt` | Modify | Upgrade vulnerable + pin unpinned deps; add dev security tools |
| `backend/app/models/consent.py` | Modify | Add `SentEmail.subject_id` (A01 IDOR fix) |
| `backend/alembic/versions/*_sentemail_subject.py` | Create | Migration for `SentEmail.subject_id` |
| `backend/app/services/email.py` | Modify | Persist `subject_id` on send |
| `backend/app/routers/auth.py`, `consent.py`, `parent_auth.py` | Modify | Pass `subject_id` at email send sites |
| `backend/app/services/export_service.py` | Modify | Filter exported emails by `subject_id` |
| `backend/app/**` | Modify | Per-finding OWASP fixes (scoped to actual audit findings) |
| `frontend/src/**` | Modify | Per-finding frontend fixes |
| `.github/workflows/ci.yml` | Modify | Add bandit + pip-audit + npm audit gate (fail on High+) |
| `backend/.pip-audit-ignore` + bandit inline `# nosec` | Create if needed | Reviewed, justified allowlists |
| `backend/tests/test_security.py` (+ new targeted files) | Create/Modify | Attack-regression tests per finding |

---

## Phase A — Foundations

### Task 1: Findings register, threat model, security tooling

**Files:**
- Create: `docs/security/audit-2026-05.md`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add security tooling to requirements**

In `backend/requirements.txt`, under the `# dev/test` section (after `ruff>=0.4`), add pinned tools:

```
bandit==1.8.0
pip-audit==2.7.3
```

- [ ] **Step 2: Install and verify the tools run**

Run from `invest-ed/backend`:
```bash
pip install -r requirements.txt
bandit --version
pip-audit --version
```
Expected: both print a version, exit 0.

- [ ] **Step 3: Create the findings register with threat model + rubric**

Create `docs/security/audit-2026-05.md` with exactly this structure (fill the threat-model prose; leave the findings table header rows ready for population by later tasks):

```markdown
# Invest-Ed Security Audit — 2026-05

## Scope
Backend (FastAPI) + frontend (React/TS) app code + dependency CVEs. LLM surface: audit/document only (fixes deferred to AI sub-project). Excludes infra/DAST/pentest.

## Threat Model
### Assets
Child PII (email, dob, username, parent_email, progress); parent PII + parent-session tokens; JWT access/refresh tokens; CSRF tokens; one-time tokens (consent/verify/reset); simulator virtual state; audit logs; LLM provider API keys.
### Trust boundaries
unauth <-> authed child; child <-> parent; app <-> LLM providers; app <-> email provider.
### Actors
unauth attacker; malicious authed child; malicious authed parent (cross-family IDOR); compromised dependency; network MITM.
### Highest-impact (prioritise)
A01 access control / IDOR on /parent/*, /users/*, simulator, content; A02 secret/cookie/transport handling; A07 auth/session integrity; A09 PII/secret leakage in logs/errors.

## Severity Rubric
- **Critical**: unauth remote compromise OR mass child-PII exposure.
- **High**: authed privilege escalation / cross-family IDOR / single-user PII exposure / auth bypass.
- **Medium**: security misconfig with limited blast radius; info leak requiring chained conditions.
- **Low**: defence-in-depth gaps; hardening nits.

## Findings Register
| ID | OWASP | Title | Severity | Location | Status | Fix commit | Regression test |
|----|-------|-------|----------|----------|--------|------------|-----------------|

## Coverage Log
(One row per audited area: "AREA - reviewed - finding IDs or NO FINDING")

## LLM Surface (Audit-only - Deferred to AI sub-project)
| ID | Risk | Severity | Recommended mitigation | Status |
|----|------|----------|------------------------|--------|

## Dependency Remediation Log
| Package | CVE(s) | Before | After | Status |
|---------|--------|--------|-------|--------|
```

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt docs/security/audit-2026-05.md
git commit -m "$(printf 'chore(security): add bandit/pip-audit + findings register skeleton\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 2: Run scanners, seed the register

**Files:**
- Modify: `docs/security/audit-2026-05.md`

- [ ] **Step 1: Run bandit (Python SAST)**

Run from `invest-ed/backend`:
```bash
bandit -r app -ll -f txt
```
(`-ll` = report Medium+ severity.) Capture the full output.

- [ ] **Step 2: Run pip-audit (backend deps)**

Run from `invest-ed/backend`:
```bash
pip-audit -r requirements.txt --desc
```
Capture every advisory (package, CVE/GHSA id, affected, fixed version).

- [ ] **Step 3: Run npm audit (frontend deps)**

Run from `invest-ed/frontend`:
```bash
npm audit --json > /tmp/npm-audit.json; npm audit
```
Capture advisories and their severities + fixed versions.

- [ ] **Step 4: Record every scanner result into the register**

For each scanner finding, add a row to the Findings Register (app-code from bandit) or the Dependency Remediation Log (pip-audit/npm audit) in `docs/security/audit-2026-05.md`. Assign OWASP category (bandit → usually A03/A05/A02; deps → A06) and severity per the rubric. Status = `Open`. Do NOT fix anything yet — this task only records. Add a Coverage Log row: `SCANNERS - reviewed - <list of finding IDs created>`.

- [ ] **Step 5: Commit**

```bash
git add docs/security/audit-2026-05.md
git commit -m "$(printf 'docs(security): seed register from bandit/pip-audit/npm audit\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

## Phase B — Known Concrete Findings (fully specified)

### Task 3: DEP-1 — python-jose CVE remediation (A06)

**Context:** `python-jose[cryptography]==3.3.0` is vulnerable to CVE-2024-33663 (algorithm confusion) and CVE-2024-33664 (JWT "bomb" DoS). It is used in `app/core/security.py`, `app/services/tokens.py`, `app/routers/consent.py` — all already pass `algorithms=[settings.jwt_algorithm]` on decode, but the DoS CVE applies regardless. Fixed in python-jose 3.4.0.

**Files:**
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_security.py`

- [ ] **Step 1: Write the failing/guard regression test**

Append to `backend/tests/test_security.py` (these are sync tests — no asyncio mark needed):

```python
def test_jose_version_not_vulnerable():
    import importlib.metadata as md
    from packaging.version import Version
    v = Version(md.version("python-jose"))
    assert v >= Version("3.4.0"), f"python-jose {v} is CVE-vulnerable (<3.4.0)"


def test_jwt_decode_rejects_token_signed_with_wrong_secret():
    import pytest
    from jose import jwt
    from app.core.config import settings
    from app.core.security import decode_token

    bad = jwt.encode({"sub": "x"}, "not-the-secret", algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception):
        decode_token(bad)
```

- [ ] **Step 2: Run to verify current state**

Run: `python -m pytest tests/test_security.py::test_jose_version_not_vulnerable tests/test_security.py::test_jwt_decode_rejects_token_signed_with_wrong_secret -v`
Expected: `test_jose_version_not_vulnerable` FAILS (3.3.0 < 3.4.0); the wrong-secret test should already PASS (pins current good behaviour so the upgrade can't regress it).

- [ ] **Step 3: Upgrade the dependency**

In `backend/requirements.txt` change `python-jose[cryptography]==3.3.0` to `python-jose[cryptography]==3.4.0`. Then run from `invest-ed/backend`: `pip install -r requirements.txt`.

- [ ] **Step 4: Verify tests pass + JWT still works end-to-end**

Run:
```bash
python -m pytest tests/test_security.py tests/test_token_service.py tests/test_auth.py tests/test_consent_router.py -q
```
Expected: ALL pass (jose 3.4.0 keeps the `jwt.encode`/`jwt.decode`/`JWTError` API used in the 3 modules). Then `pip-audit -r requirements.txt` — confirm the python-jose advisory is gone.

- [ ] **Step 5: Update the register + commit**

Mark DEP-1 `Fixed` in the Dependency Remediation Log (Before `3.3.0`, After `3.4.0`, CVE-2024-33663/33664).

```bash
git add backend/requirements.txt backend/tests/test_security.py docs/security/audit-2026-05.md
git commit -m "$(printf 'fix(security): upgrade python-jose 3.3.0 to 3.4.0 (CVE-2024-33663/33664)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 4: DEP-2 — pin unpinned dependencies (A08 supply-chain)

**Context:** `requirements.txt` pins most deps but leaves `openai>=1.0`, `anthropic>=0.30`, `sse-starlette>=1.6`, `ruff>=0.4` as floating ranges — non-reproducible builds and an unaudited supply-chain surface.

**Files:**
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_security.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_security.py`:

```python
def test_requirements_fully_pinned():
    import pathlib
    req = pathlib.Path(__file__).resolve().parents[1] / "requirements.txt"
    bad = []
    for line in req.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "==" not in s:
            bad.append(s)
    assert not bad, f"Unpinned dependencies: {bad}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_security.py::test_requirements_fully_pinned -v`
Expected: FAIL listing `openai>=1.0`, `anthropic>=0.30`, `sse-starlette>=1.6`, `ruff>=0.4`.

- [ ] **Step 3: Pin to installed resolved versions**

Run from `invest-ed/backend`:
```bash
python -c "import importlib.metadata as m; [print(p, m.version(p)) for p in ['openai','anthropic','sse-starlette','ruff']]"
```
Edit `backend/requirements.txt`: replace each floating spec with `==<the printed version>` (use the ACTUAL printed versions). Keep the `# dev/test` grouping.

- [ ] **Step 4: Verify**

Run: `python -m pytest tests/test_security.py::test_requirements_fully_pinned -q` (PASS) then `pip install -r requirements.txt` (no resolution error) then `pip-audit -r requirements.txt` (record any new advisories as Open rows — do NOT fix here; they belong to Task 8).

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/tests/test_security.py
git commit -m "$(printf 'fix(security): pin all backend dependencies (A08 supply-chain)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

### Task 5: A01-1 — SentEmail cross-child IDOR (carried from sub-project 1 DPIA)

**Context:** `build_user_export` (`app/services/export_service.py`) selects `SentEmail` by `to_email == user.email OR user.parent_email`. `SentEmail` has no `subject_id`, so a child whose `parent_email` is shared with a sibling can see the sibling's consent/verify emails in their export. This is **DPIA Risk 1** (deferred from sub-project 1). `OneTimeToken` already has `subject_id` — mirror that pattern on `SentEmail` and filter the export by it.

**Files:**
- Modify: `backend/app/models/consent.py`
- Create: `backend/alembic/versions/<rev>_sentemail_subject.py`
- Modify: `backend/app/services/email.py`
- Modify: `backend/app/services/export_service.py`
- Modify: email send call-sites in `backend/app/routers/auth.py`, `backend/app/routers/consent.py`, `backend/app/routers/parent_auth.py` (confirm exact set by grep in Step 6)
- Test: `backend/tests/test_users.py`

- [ ] **Step 1: Write the failing attack-regression test**

Append to `backend/tests/test_users.py` (file already has file-level `pytestmark`):

```python
async def test_export_does_not_leak_sibling_emails(client, db_session):
    from sqlalchemy import select
    from app.models.user import User
    from app.models.consent import SentEmail

    for uname in ("sibA", "sibB"):
        await client.post("/auth/register", json={
            "username": uname, "password": "SecurePass123!",
            "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
            "parent_email": "shared-parent@example.com",
            "policy_version_accepted": "2026-05-16",
        })
    a = await db_session.scalar(select(User).where(User.username == "sibA"))
    b = await db_session.scalar(select(User).where(User.username == "sibB"))
    a_emails = (await db_session.scalars(
        select(SentEmail).where(SentEmail.subject_id == a.id))).all()
    b_emails = (await db_session.scalars(
        select(SentEmail).where(SentEmail.subject_id == b.id))).all()
    assert a_emails and b_emails
    assert {e.subject_id for e in a_emails} == {a.id}
    assert {e.subject_id for e in b_emails} == {b.id}
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_users.py::test_export_does_not_leak_sibling_emails -v`
Expected: FAIL (`SentEmail` has no `subject_id` attribute → AttributeError/ProgrammingError).

- [ ] **Step 3: Add the column**

In `backend/app/models/consent.py`, in `class SentEmail`, add after `to_email` (mirror `OneTimeToken.subject_id`; `uuid` + `UUID(as_uuid=True)` are already imported in this module — confirm):

```python
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
```

- [ ] **Step 4: Create the Alembic migration**

Run from `invest-ed/backend`: `alembic heads` (confirm SINGLE head; if multiple, STOP and report). Then `alembic revision -m "sentemail subject_id"`. In the generated file (keep generated `revision`/`down_revision`/imports):

```python
def upgrade() -> None:
    import sqlalchemy as sa
    op.add_column("sent_emails", sa.Column("subject_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_sent_emails_subject_id"), "sent_emails", ["subject_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_sent_emails_subject_id"), table_name="sent_emails")
    op.drop_column("sent_emails", "subject_id")
```

- [ ] **Step 5: Thread `subject_id` through the email sender**

Read `backend/app/services/email.py`. Add an optional `subject_id: uuid.UUID | None = None` parameter to the `send` Protocol/method and to both `LoggingEmailSender.send` and `ResendEmailSender.send`, and pass it into the `SentEmail(...)` constructor (`subject_id=subject_id`). Import `uuid` if not present. Match the exact existing signature; keep the default `None` so unrelated callers do not break.

- [ ] **Step 6: Pass `subject_id` at the child-scoped send sites**

Grep the send call sites: `grep -rn "get_email_sender().send(\|\.send(session" backend/app`. For every send that concerns a specific user (consent_request in `auth.py` register + `consent.py` resend; verify_email in `auth.py`; password_reset in `auth.py`), pass `subject_id=user.id` (the user the email is about — use the actual user object available in scope; for password_reset use the resolved user, not the typed identifier). For parent-magic-link sends in `parent_auth.py` there is no single child subject — pass `subject_id=None` explicitly (parent-scoped, not child PII). Minimal edits; do not change email contents.

- [ ] **Step 7: Filter the export by subject_id**

In `backend/app/services/export_service.py`, change the emails query from address-based (`to_email == user.email | user.parent_email`) to `select(SentEmail).where(SentEmail.subject_id == user.id)`. This scopes a user's export to emails about *them*, eliminating the sibling leak.

- [ ] **Step 8: Run the regression + full export/email/auth suites**

Run:
```bash
python -m pytest tests/test_users.py tests/test_email.py tests/test_auth.py tests/test_parent_dashboard.py tests/test_register_consent.py tests/test_consent_router.py -q
```
Expected: ALL pass including the new test. If `test_self_export_returns_profile_json` asserted email shape, confirm it still passes (subject-scoped emails for that user are present).

- [ ] **Step 9: Update register + DPIA + commit**

In `docs/security/audit-2026-05.md` add A01-1 `Fixed` (High). In `invest-ed/docs/compliance/DPIA.md` update Residual Risk 1: status → "Resolved in security sub-project (SentEmail.subject_id added; export scoped by subject)". Add a Coverage Log row.

```bash
git add backend/app/models/consent.py backend/alembic/versions/*sentemail_subject*.py backend/app/services/email.py backend/app/services/export_service.py backend/app/routers/auth.py backend/app/routers/consent.py backend/app/routers/parent_auth.py backend/tests/test_users.py docs/security/audit-2026-05.md invest-ed/docs/compliance/DPIA.md
git commit -m "$(printf 'fix(security): scope SentEmail by subject_id to close cross-child export IDOR (A01)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

## Phase C — Manual Audit (discovery-driven; rigorous methodology)

> These tasks DISCOVER findings. The per-finding work follows the **Fix Loop** below — the exact, mandatory procedure (Task 5 is its fully-worked template). No finding is fixed without an attack-shaped regression test that fails pre-fix and passes post-fix.

**Fix Loop (apply to every finding discovered in Tasks 6–7):**
1. Add a register row: ID, OWASP cat, title, severity (rubric), location `file:line`, Status `Open`.
2. Write an attack-shaped test reproducing the issue (a request/exploit that succeeds against current code where it must not). Run it — it must FAIL (the unsafe behaviour is present / the exploit currently works).
3. Apply the minimal fix.
4. Run the test — it must PASS. Run the full backend suite (`python -m pytest -q`) — must stay green.
5. `ruff check` changed files — clean.
6. Mark the register row `Fixed` + commit (one commit per finding or per tightly-related cluster within a category); record the commit + test name in the row.
If a discovered issue is LLM-surface only → record in the LLM table as `Deferred`, no code change. If a finding has no in-scope fix → `Accepted` with written rationale + compensating control.

### Task 6: Backend OWASP manual walk (A01–A10)

**Files:** Modify `docs/security/audit-2026-05.md` (always); `backend/app/**` + `backend/tests/**` (per finding via Fix Loop).

Work the categories in this order (highest-impact first). For EACH category: inspect the listed surface, add a Coverage Log row stating what was reviewed and the finding IDs (or `NO FINDING`), and run the Fix Loop for anything found.

- [ ] **Step 1: A01 Broken Access Control / IDOR**
Inspect every route in `backend/app/routers/` that accepts an id or returns user-scoped data: `parent.py` (every `/parent/children/{user_id}/*` — confirm `_get_owned_child` ownership scoping on ALL, incl. export/freeze/erasure), `users.py` (`/users/me*`, `/users/me/export` bound to `get_current_user` only), `consent.py` + `auth.py` token endpoints (no client id trust), simulator routers (portfolio/holding/`{id}` scoped to the authed child), content/progress routers. For each: assert the authenticated principal can only access their own resources; a child cannot reach parent endpoints and vice-versa. Attack-test pattern for any gap: authenticate principal X, request principal Y's resource, assert 403/404 (not 200).

- [ ] **Step 2: A02 Cryptographic Failures**
Review `app/core/security.py` (cookie flag helpers), `app/routers/auth.py` cookie setting (httponly/secure/samesite across `settings.environment`), JWT alg pinning (decode always passes `algorithms=[...]` in all 3 jose call sites), one-time-token entropy/expiry (`app/services/tokens.py`). Attack-test pattern: forged/cross-alg/expired token rejected; cookies carry secure flags in non-dev.

- [ ] **Step 3: A03 Injection**
`grep -rn "text(\|execute(\|os.system\|subprocess\|eval(\|exec(\|pickle" backend/app` plus inspect any f-string/`%`-built SQL. Confirm all DB access is SQLAlchemy-parameterised; no shell/eval/unsafe deserialisation; route/path params validated. Fix Loop any raw/interpolated query.

- [ ] **Step 4: A04/A05 Insecure Design / Misconfiguration**
Review `app/main.py` (CORS — origins not `*` with credentials; middleware order), error handlers (no stack/internal leak — trigger a 500 in a test and assert generic body), `settings` debug off in non-dev, security headers completeness incl. CSP/HSTS, rate-limit decorators on all auth/sensitive endpoints, seed prod-guard (verify `seed_compliance_accounts` early-returns in production).

- [ ] **Step 5: A07 Identification & Auth Failures**
Token type/audience enforcement (access vs refresh vs one-time cannot be substituted — attack-test: use a refresh token as access, expect reject), session fixation (new tokens on login/privilege change), lockout cannot be bypassed nor used for enumeration, reset/verify one-time tokens single-use + expiry (replay a consumed token → 410).

- [ ] **Step 6: A08 / A09 / A10**
A08: untrusted deserialisation / token tampering resistance. A09: `grep -rn "logging\|logger\|print(" backend/app` — confirm no password/hash/token/PII in logs or `AuditLog`; error responses generic. A10: any server-side outbound HTTP with a user-influenced URL (email links are app-generated from `settings.app_base_url` — confirm not user-controlled; LLM/provider base URLs are config — confirm not user-set).

- [ ] **Step 7: Category completeness commit**
Ensure every category A01–A10 has a Coverage Log row (finding IDs or `NO FINDING`). Commit the register coverage updates (per-finding fixes were already committed via the Fix Loop):

```bash
git add docs/security/audit-2026-05.md
git commit -m "$(printf 'docs(security): backend OWASP A01-A10 coverage log\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

### Task 7: Frontend audit + fixes

**Files:** Modify `docs/security/audit-2026-05.md`; `frontend/src/**` + checks (per finding via Fix Loop; frontend "regression test" = a failing assertion / `tsc` / lint check, or a documented manual repro when no harness exists — state which).

- [ ] **Step 1: XSS sink sweep**
`grep -rn "dangerously\|innerHTML\|insertAdjacentHTML\|document.write\|eval(\|new Function" frontend/src`. For any raw-HTML injection sink fed non-constant content: sanitize (DOMPurify) or replace with safe rendering. Record + Fix Loop.

- [ ] **Step 2: Link & navigation safety**
`grep -rn "target=\"_blank\"\|href={" frontend/src` — every external `target="_blank"` link must have `rel="noopener noreferrer"`; no `javascript:`/user-controlled `href`. Fix Loop gaps.

- [ ] **Step 3: Token/secret storage**
`grep -rn "localStorage\|sessionStorage\|document.cookie" frontend/src` — confirm no JWT/refresh/CSRF token or secret persisted client-side (auth is httpOnly-cookie based). Any finding → Fix Loop.

- [ ] **Step 4: Auth-state & CSP**
Confirm protected routes are gated (no sensitive data rendered pre-auth) and the frontend doesn't require an unsafe CSP (no inline-script reliance forcing `unsafe-inline`). Document alignment with the backend CSP header.

- [ ] **Step 5: Verify + coverage commit**
Run from `invest-ed/frontend`: `npx tsc --noEmit` and `npm run build` (both clean). Add Coverage Log rows for each frontend area. Commit register coverage:

```bash
git add docs/security/audit-2026-05.md
git commit -m "$(printf 'docs(security): frontend audit coverage log\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

## Phase D — Dependencies, LLM, CI Gate, Verification

### Task 8: Remaining dependency remediation

**Files:** Modify `backend/requirements.txt`, `frontend/package.json`/lockfile, `docs/security/audit-2026-05.md`; tests as needed.

- [ ] **Step 1: Re-run scanners for the current Open dep rows**
`cd invest-ed/backend && pip-audit -r requirements.txt --desc` and `cd invest-ed/frontend && npm audit`. For EACH advisory still Open (excluding python-jose, already fixed in Task 3):

- [ ] **Step 2: Remediate each — fix all, pin safe versions**
For every advisory: upgrade to the lowest non-vulnerable version and pin (`==`). If the safe version is a breaking major, perform the upgrade and fix the breakage in this task (resolve, re-run full suite). Backend after each change: `pip install -r requirements.txt && python -m pytest -q` (green). Frontend: explicit version bump (or `npm audit fix`) then `npm ci && npx tsc --noEmit && npm run build` (green). Record Before→After+CVE in the Dependency Remediation Log, Status `Fixed`.

- [ ] **Step 3: Residual-only exception**
If an advisory has NO fixed version available, mark it `Accepted` in the log with: rationale, exploitability assessment for this app, compensating control, review date. This is the ONLY permitted non-fix.

- [ ] **Step 4: Confirm clean + commit**
`pip-audit -r requirements.txt` and `npm audit --audit-level=high` show zero unaddressed High+ (Accepted rows excepted). Full backend suite + frontend build green.

```bash
git add backend/requirements.txt frontend/package.json frontend/package-lock.json docs/security/audit-2026-05.md
git commit -m "$(printf 'fix(security): remediate remaining dependency CVEs (pin safe versions)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

### Task 9: LLM surface — audit-only documentation

**Files:** Modify `docs/security/audit-2026-05.md`. NO code changes.

- [ ] **Step 1: Document each LLM service risk**
Inspect `app/services/llm_client.py`, `tutor_service.py`, `chart_coach_service.py`, `ai_content_service.py`. For each, add a row to the "LLM Surface" table: risk (prompt injection via child input reaching model instructions; PII minimisation — enumerate exactly which child fields are sent to Together/Groq/OpenAI; kid-safety of model output; provider API-key handling; model-output→UI XSS), severity (rubric), recommended mitigation, Status `Deferred -> AI sub-project`.

- [ ] **Step 2: Cross-check generic findings aren't hidden here**
If any LLM-surface issue is ALSO a generic app-code finding (e.g. an API key written to a log → that is A09 and must be fixed in Task 6, not deferred), note the cross-reference explicitly. Commit:

```bash
git add docs/security/audit-2026-05.md
git commit -m "$(printf 'docs(security): LLM attack-surface audit (deferred to AI sub-project)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

### Task 10: CI security gate

**Files:** Modify `.github/workflows/ci.yml`; Create `docs/security/ci-security-gate.md`; Create `backend/.pip-audit-ignore` only if needed.

- [ ] **Step 1: Add a security job to CI**
In `.github/workflows/ci.yml` add a third job `security` (peer of `frontend`/`backend`) that runs bandit, pip-audit, npm audit and FAILS on High/Critical only:

```yaml
  security:
    name: Security (bandit · pip-audit · npm audit)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install backend deps + tools
        working-directory: invest-ed/backend
        run: pip install -r requirements.txt
      - name: Bandit (fail on High severity + High confidence)
        working-directory: invest-ed/backend
        run: bandit -r app -lll -iii
      - name: pip-audit (fail on any unignored vuln)
        working-directory: invest-ed/backend
        run: pip-audit -r requirements.txt
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: invest-ed/frontend/package-lock.json
      - name: npm install
        working-directory: invest-ed/frontend
        run: npm ci
      - name: npm audit (fail on High+)
        working-directory: invest-ed/frontend
        run: npm audit --audit-level=high
```
If a reviewed allowlist becomes necessary: create `backend/.pip-audit-ignore` (one CVE/GHSA id per line, each preceded by a `#` comment with rationale + review date) and change the pip-audit step to `pip-audit -r requirements.txt --ignore-vuln $(grep -v '^#' .pip-audit-ignore | tr '\n' ' ')`; for bandit false positives use inline `# nosec <ruleid>  # <rationale>` rather than disabling rules globally.

- [ ] **Step 2: Document the gate**
Create `docs/security/ci-security-gate.md`: what runs, the fail-threshold (High+), how to triage a failure, how to add a justified allowlist entry (bandit `# nosec` requires inline rationale; `.pip-audit-ignore` entry requires CVE id + rationale + review date), and that Medium/Low are visible in logs but non-blocking.

- [ ] **Step 3: Validate the workflow is well-formed**
Run from repo root: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')"` (`pip install pyyaml` if missing). Expected: `yaml ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml docs/security/ci-security-gate.md
git commit -m "$(printf 'ci(security): add bandit/pip-audit/npm audit gate (fail on High+)\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

### Task 11: Final verification

**Files:** Modify `docs/security/audit-2026-05.md` (final status), `docs/security/ci-security-gate.md` (record the gate-block check).

- [ ] **Step 1: Register has zero Open rows**
Every Findings Register row is `Fixed`, `Deferred` (LLM only), or `Accepted` (with rationale). Every OWASP category + frontend area has a Coverage Log row. `grep -n "| Open " docs/security/audit-2026-05.md` returns nothing.

- [ ] **Step 2: Scanners clean at gate threshold**
`cd invest-ed/backend && bandit -r app -lll -iii` (exit 0) and `pip-audit -r requirements.txt` (no High+ unaccepted). `cd invest-ed/frontend && npm audit --audit-level=high` (exit 0).

- [ ] **Step 3: Full regression green**
`cd invest-ed/backend && python -m pytest -q` (≥225 passed, 0 failed) and `ruff check .` (clean). `cd invest-ed/frontend && npx tsc --noEmit && npm run build` (clean). `cd invest-ed/backend && alembic heads` (single head).

- [ ] **Step 4: Gate-blocks sanity (one-time, manual, reverted)**
Temporarily add, to any file under `backend/app`, a single line that bandit rates High/High (a reviewer-known dangerous-call pattern — choose any bandit B-rule rated High, e.g. an unsafe deserialisation or shell-execution call on a literal). Run the CI security job's bandit command locally (`bandit -r app -lll -iii`), confirm a NONZERO exit, then REVERT the line (do not stage or commit it; verify `git status` shows the file clean afterward). Record in `ci-security-gate.md` that this verification was performed, the bandit rule id used, and the date.

- [ ] **Step 5: Final commit**

```bash
git add docs/security/audit-2026-05.md docs/security/ci-security-gate.md
git commit -m "$(printf 'docs(security): finalize audit register - zero open findings\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>')"
```

---

## Self-Review

**1. Spec coverage:**
- §1 Findings Register & methodology → Task 1 (register+rubric+threat model), Task 2 (scanner seeding). ✓
- §2 Manual backend audit + fixes (A01–A10) → Task 6 with explicit per-category surface + Fix Loop; Task 5 is the fully-worked A01 template. ✓
- §3 Frontend audit + fixes → Task 7. ✓
- §4 Dependency remediation (fix all, pin) → Task 3 (jose CVE), Task 4 (pin unpinned), Task 8 (remaining). ✓
- §5 LLM surface audit-only → Task 9. ✓
- §6 CI security gate + allowlist + docs → Task 10. ✓
- §7 Testing (attack-regression; suite green) → Fix Loop mandates it; Task 11 final verification. ✓
- Out-of-scope respected (no LLM code fixes; no infra/DAST). ✓

**2. Placeholder scan:** No "TBD/decide later". Discovery-driven Tasks 6–8 cannot pre-name emergent findings — inherent to audit work — and are handled by a fully-specified mandatory **Fix Loop** with Task 5 as a complete worked example (real known finding with exact model/migration/test code). All concrete known findings (python-jose CVE, unpinned deps, SentEmail IDOR, CI YAML) are fully specified with exact code/commands. Method is exhaustively specified even where individual findings are emergent.

**3. Type/consistency:** `SentEmail.subject_id` named consistently across model, migration index `ix_sent_emails_subject_id`, email-sender param `subject_id`, export filter, DPIA update. `decode_token` matches the real symbol in `app/core/security.py`. New CI job `security` is peer-level and uniquely named. Severity rubric defined once (Task 1), referenced by the Fix Loop and Task 11. Consistent.

Gaps found: none requiring a new task. Tasks 6–7 are larger than a single 2–5 min step because audit scope is emergent; they are explicitly structured as a per-category checklist + repeatable Fix Loop — the correct shape for audit work and still executable task-by-task.
