# Compliance + Auth Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add email verification, age-split password reset, GDPR export, a data-retention purge job, and UK-AADC net-new privacy standards, all driven by a single centralised compliance-policy resolver keyed on the user's jurisdiction.

**Architecture:** One new module `app/services/compliance.py` resolves a frozen `CompliancePolicy` from `country_code` + `dob`. The existing `consent_service` becomes a thin delegating wrapper so all current behaviour and tests are preserved. New auth endpoints reuse the existing `OneTimeToken` JWT machinery (`app/services/tokens.py`) and the existing email abstraction (`app/services/email.py`, `LoggingEmailSender` in dev/test). New nullable columns are added to `users` via one Alembic migration.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2 (async), Alembic, pydantic v2, pytest + pytest-asyncio (`loop_scope="session"`), httpx ASGI test client, React + TypeScript (Vite) frontend, ruff.

**Working directory:** `/Users/leeashmore/Local Repo/invest-ed`. All backend paths below are relative to `invest-ed/backend/`. Run all backend commands from `invest-ed/backend/`.

**Test conventions (read before starting):**
- Every backend test module starts with `import pytest` and `pytestmark = pytest.mark.asyncio(loop_scope="session")`.
- Fixtures from `tests/conftest.py`: `db_session` (rolled-back AsyncSession), `client` (httpx AsyncClient over the ASGI app, with `get_session` overridden to `db_session`). `settings.email_backend` is forced to `"logging"` in conftest, so all sent email is written to the `sent_emails` table (model `app.models.consent.SentEmail`) and nothing leaves the process.
- To assert an email was "sent", query `SentEmail` rows via `db_session`.
- CSRF: `GET/HEAD/OPTIONS` are always exempt. New pre-auth POST endpoints must be added to `_DEFAULT_EXEMPT_PATHS` in `app/core/csrf.py` (same as `/auth/login`).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `app/services/compliance.py` | Create | `Regime` enum, `CompliancePolicy` dataclass, `resolve_policy()`, jurisdiction tables |
| `app/services/consent_service.py` | Modify | Delegate `consent_threshold`/`needs_parental_consent` to `resolve_policy` |
| `app/models/user.py` | Modify | New nullable columns; make `email` nullable |
| `alembic/versions/<rev>_compliance_auth.py` | Create | Migration for new columns + `email` nullable |
| `app/core/config.py` | Modify | `data_retention_days`, `privacy_notice_version` |
| `app/services/tokens.py` | Modify | `VERIFY_EMAIL_*`, `PASSWORD_RESET_*` audiences/expiries |
| `app/services/email.py` | Modify | `verify_email`, `password_reset` templates (plain + HTML + subject) |
| `app/schemas/auth.py` | Modify | Optional child `email`, `policy_version_accepted`; login by identifier |
| `app/routers/auth.py` | Modify | Register flow via resolver; verify-email + forgot/reset endpoints; login by identifier |
| `app/core/csrf.py` | Modify | Exempt `/auth/forgot-password`, `/auth/reset-password` |
| `app/services/retention.py` | Create | `purge_expired_accounts()` |
| `app/cli.py` | Create | `purge-accounts` CLI command |
| `app/routers/users.py` | Modify | `GET /users/me/export` |
| `app/routers/parent.py` | Modify | `GET /parent/children/{user_id}/export` |
| `app/services/export_service.py` | Create | Build the GDPR export dict (shared by self + parent) |
| `app/seed/compliance_accounts.py` | Create | Idempotent dev/test seed accounts |
| `docs/compliance/DPIA.md` | Create | Data-protection impact assessment |
| `docs/compliance/privacy-notice.md` | Create | Child-friendly privacy notice source of truth |
| `docs/compliance/operations.md` | Create | Purge cron runbook |
| `frontend/src/pages/child/Signup.tsx` | Modify | Privacy-notice acknowledgement control |
| `frontend/src/pages/Login.tsx` (or child Login) | Modify | "Forgot password?" link |
| `frontend/src/pages/ForgotPassword.tsx` | Create | Email-entry form |
| `frontend/src/pages/ResetPassword.tsx` | Create | Token + new-password form |
| `frontend/src/pages/VerifyEmail.tsx` | Create | Token landing page |
| `frontend/src/components/VerifyEmailBanner.tsx` | Create | Unverified reminder banner |
| `frontend/src/App.tsx` | Modify | Routes for new pages |
| Tests across `tests/` | Create/Modify | Unit + integration coverage |

---

### Task 1: Compliance Policy Core

**Files:**
- Create: `app/services/compliance.py`
- Test: `tests/test_compliance.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_compliance.py`:

```python
from datetime import date

import pytest

from app.services.compliance import Regime, resolve_policy

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _dob_for_age(age: int, today: date) -> date:
    return date(today.year - age, today.month, today.day)


def test_gb_under_13_requires_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("GB", _dob_for_age(12, today), today)
    assert p.regime is Regime.UK_AADC
    assert p.consent_age == 13
    assert p.requires_parental_consent is True
    assert p.email_verification_target == "parent"
    assert p.password_reset_mode == "parent"
    assert p.data_retention_days == 30
    assert p.profiling_default_off is True


def test_gb_13_does_not_require_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("GB", _dob_for_age(13, today), today)
    assert p.requires_parental_consent is False
    assert p.email_verification_target == "self"
    assert p.password_reset_mode == "self"


def test_ie_under_16_requires_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("IE", _dob_for_age(15, today), today)
    assert p.regime is Regime.EU_GDPRK
    assert p.consent_age == 16
    assert p.requires_parental_consent is True


def test_ie_16_does_not_require_consent():
    today = date(2026, 5, 16)
    p = resolve_policy("IE", _dob_for_age(16, today), today)
    assert p.requires_parental_consent is False


def test_us_under_13_is_coppa():
    today = date(2026, 5, 16)
    p = resolve_policy("US", _dob_for_age(12, today), today)
    assert p.regime is Regime.COPPA
    assert p.consent_age == 13
    assert p.requires_parental_consent is True


def test_hk_under_13_is_pdpo():
    today = date(2026, 5, 16)
    p = resolve_policy("HK", _dob_for_age(12, today), today)
    assert p.regime is Regime.HK_PDPO
    assert p.consent_age == 13


def test_unknown_country_defaults_to_13():
    today = date(2026, 5, 16)
    p = resolve_policy("ZZ", _dob_for_age(12, today), today)
    assert p.regime is Regime.DEFAULT
    assert p.consent_age == 13
    assert p.requires_parental_consent is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_compliance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.compliance'`.

- [ ] **Step 3: Write the implementation**

Create `app/services/compliance.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.services.consent_service import age_in_years

_EU_GDPRK_COUNTRIES: frozenset[str] = frozenset({
    "IE", "NL", "DE", "LU", "SK", "HR", "FR", "ES", "IT", "BE", "AT",
    "PT", "PL", "SE", "DK", "FI", "CZ", "HU", "RO", "BG", "GR", "EE",
    "LV", "LT", "SI", "CY", "MT",
})
# Member states whose GDPR-K consent age is 16 (others in the EU set use 13).
_EU_CONSENT_AGE_16: frozenset[str] = frozenset({"IE", "NL", "DE", "LU", "SK", "HR"})


class Regime(str, Enum):
    UK_AADC = "UK_AADC"
    COPPA = "COPPA"
    EU_GDPRK = "EU_GDPRK"
    HK_PDPO = "HK_PDPO"
    DEFAULT = "DEFAULT"


@dataclass(frozen=True)
class CompliancePolicy:
    regime: Regime
    consent_age: int
    requires_parental_consent: bool
    email_verification_target: str  # "parent" | "self"
    password_reset_mode: str        # "parent" | "self"
    data_retention_days: int
    profiling_default_off: bool


def _regime_for(country_code: str) -> Regime:
    cc = country_code.upper()
    if cc == "GB":
        return Regime.UK_AADC
    if cc == "US":
        return Regime.COPPA
    if cc == "HK":
        return Regime.HK_PDPO
    if cc in _EU_GDPRK_COUNTRIES:
        return Regime.EU_GDPRK
    return Regime.DEFAULT


def _consent_age_for(country_code: str, regime: Regime) -> int:
    if regime is Regime.EU_GDPRK and country_code.upper() in _EU_CONSENT_AGE_16:
        return 16
    return 13


def resolve_policy(country_code: str, dob: date, today: date) -> CompliancePolicy:
    regime = _regime_for(country_code)
    consent_age = _consent_age_for(country_code, regime)
    needs_consent = age_in_years(dob, today) < consent_age
    target = "parent" if needs_consent else "self"
    return CompliancePolicy(
        regime=regime,
        consent_age=consent_age,
        requires_parental_consent=needs_consent,
        email_verification_target=target,
        password_reset_mode=target,
        data_retention_days=30,
        profiling_default_off=True,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_compliance.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/compliance.py backend/tests/test_compliance.py
git commit -m "feat: centralised compliance policy resolver"
```

---

### Task 2: Delegate consent_service to the resolver

**Files:**
- Modify: `app/services/consent_service.py`
- Test: `tests/test_consent_service.py` (existing — must stay green), add one delegation test

- [ ] **Step 1: Write the failing test**

Append to `tests/test_consent_service.py`:

```python
def test_consent_threshold_matches_resolver_for_eu16():
    # IE is a GDPR-K 16 country; threshold helper must still return 16.
    from app.services.consent_service import consent_threshold
    assert consent_threshold("IE") == 16
    assert consent_threshold("GB") == 13
    assert consent_threshold("US") == 13
```

- [ ] **Step 2: Run the full consent test file to confirm current state**

Run: `python -m pytest tests/test_consent_service.py -v`
Expected: existing tests PASS; the new test also PASSES already (current flat logic returns 16 for IE, 13 otherwise). This test pins behaviour so the refactor cannot regress it.

- [ ] **Step 3: Refactor implementation to delegate**

Replace the body of `app/services/consent_service.py` with:

```python
from datetime import date

# Kept for backwards-compatible imports (used elsewhere).
EU_COUNTRIES_16: frozenset[str] = frozenset({"IE", "NL", "DE", "LU", "SK", "HR"})


def age_in_years(dob: date, today: date) -> int:
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def consent_threshold(country_code: str) -> int:
    """Age below which parental data-consent is required."""
    # Imported here to avoid a circular import (compliance imports age_in_years).
    from app.services.compliance import _consent_age_for, _regime_for
    return _consent_age_for(country_code, _regime_for(country_code))


def needs_parental_consent(dob: date, country_code: str, today: date) -> bool:
    from app.services.compliance import resolve_policy
    return resolve_policy(country_code, dob, today).requires_parental_consent
```

- [ ] **Step 4: Run the consent + compliance + register-consent suites**

Run: `python -m pytest tests/test_consent_service.py tests/test_compliance.py tests/test_register_consent.py tests/test_consent_router.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/consent_service.py backend/tests/test_consent_service.py
git commit -m "refactor: consent_service delegates to compliance resolver"
```

---

### Task 3: User model columns + Alembic migration

**Files:**
- Modify: `app/models/user.py`
- Create: `alembic/versions/<rev>_compliance_auth.py`
- Test: `tests/test_models.py` (add one test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models.py`:

```python
async def test_user_compliance_columns_default(db_session):
    from datetime import date
    from app.models.user import User

    u = User(
        email="cols@example.com", username="colsuser", password_hash="x",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
    )
    db_session.add(u)
    await db_session.flush()
    assert u.email_verified_at is None
    assert u.purged_at is None
    assert u.profiling_enabled is False
    assert u.marketing_opt_in is False
    assert u.policy_version_accepted is None
    assert u.policy_accepted_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py::test_user_compliance_columns_default -v`
Expected: FAIL with `AttributeError: 'User' object has no attribute 'email_verified_at'`.

- [ ] **Step 3: Modify the model**

In `app/models/user.py`, change the `email` column to nullable and add the new columns. Replace line 17:

```python
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
```

Add these columns immediately after the `deleted_at` column (after line 51, before the `progress` relationship at line 53):

```python
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    profiling_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    marketing_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false", default=False
    )
    policy_version_accepted: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    policy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py::test_user_compliance_columns_default -v`
Expected: PASS. (The test DB is created from `Base.metadata.create_all`, so no migration is needed for tests — but production needs the migration below.)

- [ ] **Step 5: Generate and hand-edit the Alembic migration**

Run: `alembic revision -m "compliance auth columns"`
This creates `alembic/versions/<rev>_compliance_auth_columns.py`. Replace its `upgrade()` and `downgrade()` with:

```python
def upgrade() -> None:
    import sqlalchemy as sa
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_purged_at", "users", ["purged_at"])
    op.add_column("users", sa.Column("profiling_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("marketing_opt_in", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("policy_version_accepted", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("policy_accepted_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    import sqlalchemy as sa
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("users", "policy_accepted_at")
    op.drop_column("users", "policy_version_accepted")
    op.drop_column("users", "marketing_opt_in")
    op.drop_column("users", "profiling_enabled")
    op.drop_index("ix_users_purged_at", table_name="users")
    op.drop_column("users", "purged_at")
    op.drop_column("users", "email_verified_at")
```

(Keep the auto-generated `revision`, `down_revision`, `op` import and `from alembic import op` lines as generated.)

- [ ] **Step 6: Verify migration is syntactically valid**

Run: `python -c "import importlib, glob; [importlib.machinery.SourceFileLoader('m', f).load_module() for f in glob.glob('alembic/versions/*compliance_auth*.py')]"`
Expected: no output, exit 0 (module imports cleanly).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/user.py backend/alembic/versions/*compliance_auth*.py backend/tests/test_models.py
git commit -m "feat: add compliance/auth columns to users (+ migration)"
```

---

### Task 4: Config + token purposes

**Files:**
- Modify: `app/core/config.py`
- Modify: `app/services/tokens.py`
- Test: `tests/test_config.py`, `tests/test_token_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_config.py`:

```python
def test_compliance_config_defaults():
    from app.core.config import settings
    assert settings.data_retention_days == 30
    assert settings.privacy_notice_version == "2026-05-16"
```

Append to `tests/test_token_service.py`:

```python
async def test_verify_email_and_reset_token_roundtrip(db_session):
    import uuid
    from app.services.tokens import (
        PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY,
        VERIFY_EMAIL_AUDIENCE, VERIFY_EMAIL_EXPIRY,
        consume_one_time_token, issue_one_time_token,
    )
    uid = uuid.uuid4()
    vt = await issue_one_time_token(
        db_session, purpose=VERIFY_EMAIL_AUDIENCE, email="t@example.com",
        subject_id=uid, expires_in=VERIFY_EMAIL_EXPIRY,
    )
    row = await consume_one_time_token(db_session, vt, VERIFY_EMAIL_AUDIENCE)
    assert row.subject_id == uid

    rt = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email="t@example.com",
        subject_id=uid, expires_in=PASSWORD_RESET_EXPIRY,
    )
    row2 = await consume_one_time_token(db_session, rt, PASSWORD_RESET_AUDIENCE)
    assert row2.subject_id == uid
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py::test_compliance_config_defaults tests/test_token_service.py::test_verify_email_and_reset_token_roundtrip -v`
Expected: FAIL (`AttributeError` on `settings.data_retention_days`; `ImportError` on `VERIFY_EMAIL_AUDIENCE`).

- [ ] **Step 3: Implement config additions**

In `app/core/config.py`, add these two fields immediately after `app_base_url: str = "http://localhost:5173"` (line 18):

```python
    data_retention_days: int = 30
    privacy_notice_version: str = "2026-05-16"
```

- [ ] **Step 4: Implement token additions**

In `app/services/tokens.py`, after line 17 (`PARENT_SESSION_EXPIRY = timedelta(days=7)`), add:

```python
VERIFY_EMAIL_AUDIENCE = "verify_email"
PASSWORD_RESET_AUDIENCE = "password_reset"

VERIFY_EMAIL_EXPIRY = timedelta(hours=24)
PASSWORD_RESET_EXPIRY = timedelta(hours=1)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py::test_compliance_config_defaults tests/test_token_service.py::test_verify_email_and_reset_token_roundtrip -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/services/tokens.py backend/tests/test_config.py backend/tests/test_token_service.py
git commit -m "feat: config + token purposes for verify-email and password-reset"
```

---

### Task 5: Email templates for verify-email and password-reset

**Files:**
- Modify: `app/services/email.py`
- Test: `tests/test_email.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_email.py`:

```python
async def test_verify_email_and_reset_templates_render(db_session):
    from app.models.consent import SentEmail
    from app.services.email import LoggingEmailSender
    from sqlalchemy import select

    sender = LoggingEmailSender()
    await sender.send(db_session, "kid@example.com", "verify_email",
                      {"username": "kiddo", "link": "https://x/y?token=abc"})
    await sender.send(db_session, "kid@example.com", "password_reset",
                      {"link": "https://x/reset?token=def"})
    rows = (await db_session.scalars(select(SentEmail))).all()
    templates = {r.template for r in rows}
    assert "verify_email" in templates
    assert "password_reset" in templates
    bodies = "\n".join(r.body for r in rows)
    assert "https://x/y?token=abc" in bodies
    assert "https://x/reset?token=def" in bodies
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email.py::test_verify_email_and_reset_templates_render -v`
Expected: FAIL with `ValueError: Unknown template: verify_email`.

- [ ] **Step 3: Implement template branches**

In `app/services/email.py`, in `_render()` add these branches before the final `raise ValueError`:

```python
    if template == "verify_email":
        return (
            f"Hi {context['username']},\n\n"
            f"Please confirm your Invest-Ed email address by clicking: {context['link']}\n\n"
            f"If you didn't create an account you can ignore this email.\n"
            f"Link expires in 24 hours."
        )
    if template == "password_reset":
        return (
            f"We received a request to reset the password for an Invest-Ed account.\n"
            f"Click to choose a new password: {context['link']}\n\n"
            f"If you didn't request this, you can ignore this email.\n"
            f"Link expires in 1 hour."
        )
```

In the `_SUBJECT` dict add:

```python
    "verify_email": "Confirm your Invest-Ed email",
    "password_reset": "Reset your Invest-Ed password",
```

In `_render_html()` add these branches before the final `else: raise ValueError`:

```python
    elif template == "verify_email":
        heading = "Confirm your email"
        body_text = f"Hi {context['username']}, please confirm your Invest-Ed email address."
        cta_label = "Confirm Email"
        cta_url = context["link"]
        footer = "If you didn't create an account, ignore this email. Link expires in 24 hours."
    elif template == "password_reset":
        heading = "Reset your password"
        body_text = "Click below to choose a new password for your Invest-Ed account."
        cta_label = "Reset Password"
        cta_url = context["link"]
        footer = "If you didn't request this, ignore this email. Link expires in 1 hour."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_email.py::test_verify_email_and_reset_templates_render -v`
Expected: PASS.

- [ ] **Step 5: Run the full email suite for regression**

Run: `python -m pytest tests/test_email.py tests/test_email_service.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/email.py backend/tests/test_email.py
git commit -m "feat: verify-email and password-reset email templates"
```

---

### Task 6: Schemas — optional child email, policy acceptance, login identifier

**Files:**
- Modify: `app/schemas/auth.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas.py`:

```python
def test_register_request_email_optional_and_policy_field():
    from app.schemas.auth import RegisterRequest
    r = RegisterRequest(
        username="kid1", password="SecurePass123!", dob="2014-01-01",
        country_code="GB", currency_code="GBP", parent_email="p@example.com",
        policy_version_accepted="2026-05-16",
    )
    assert r.email is None
    assert r.policy_version_accepted == "2026-05-16"


def test_login_request_accepts_username_identifier():
    from app.schemas.auth import LoginRequest
    lr = LoginRequest(email="kiddo_username", password="whatever12345")
    # `email` field now carries an identifier (email OR username); not EmailStr.
    assert lr.email == "kiddo_username"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_schemas.py::test_register_request_email_optional_and_policy_field tests/test_schemas.py::test_login_request_accepts_username_identifier -v`
Expected: FAIL (email required → ValidationError; LoginRequest rejects non-email).

- [ ] **Step 3: Implement schema changes**

In `app/schemas/auth.py`:

Change line 13 from `email: EmailStr` to:

```python
    email: EmailStr | None = None
```

Add a new field after `topic_path` (after line 20):

```python
    policy_version_accepted: str | None = Field(default=None, max_length=20)
```

Replace the `LoginRequest` class (lines 96–103) with:

```python
class LoginRequest(BaseModel):
    # `email` carries a login identifier: an email address OR a username.
    # Username-only child accounts (registered without a child email) log in here.
    email: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalise_identifier(cls, v: str) -> str:
        return v.lower().strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_schemas.py -v`
Expected: ALL PASS (existing schema tests + 2 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/auth.py backend/tests/test_schemas.py
git commit -m "feat: optional child email, policy acceptance field, identifier login schema"
```

---

### Task 7: Register flow via resolver (consent + self verify-email + policy capture)

**Files:**
- Modify: `app/routers/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth.py`:

```python
async def test_register_teen_self_sends_verify_email(client, db_session):
    from sqlalchemy import select
    from app.models.consent import SentEmail

    resp = await client.post("/auth/register", json={
        "email": "teen@example.com", "username": "teen1",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 201
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.template == "verify_email")
    )).all()
    assert any(r.to_email == "teen@example.com" for r in rows)


async def test_register_underage_no_child_email_ok_with_parent(client):
    resp = await client.post("/auth/register", json={
        "username": "littlekid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending_consent"


async def test_register_teen_without_email_rejected(client):
    resp = await client.post("/auth/register", json={
        "username": "noemailteen", "password": "SecurePass123!",
        "dob": "2009-01-01", "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py::test_register_teen_self_sends_verify_email tests/test_auth.py::test_register_underage_no_child_email_ok_with_parent tests/test_auth.py::test_register_teen_without_email_rejected -v`
Expected: FAIL (no verify_email sent; underage-without-email currently 500/duplicate-email error path; teen-without-email currently rejected with wrong cause).

- [ ] **Step 3: Implement register changes**

In `app/routers/auth.py`:

Update the import on line 23:

```python
from app.services.consent_service import age_in_years
from app.services.compliance import resolve_policy
```

Update the token import block (lines 25–29) to also import the verify-email constants:

```python
from app.services.tokens import (
    CONSENT_AUDIENCE,
    CONSENT_EXPIRY,
    VERIFY_EMAIL_AUDIENCE,
    VERIFY_EMAIL_EXPIRY,
    issue_one_time_token,
)
```

Replace the body of `register()` from line 95 (`existing = ...`) through the end of the function (line 161) with:

```python
    if payload.email:
        existing = await session.scalar(select(User).where(User.email == payload.email))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    existing_username = await session.scalar(
        select(User).where(User.username == payload.username)
    )
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    today = date.today()
    policy = resolve_policy(payload.country_code, payload.dob, today)
    needs_consent = policy.requires_parental_consent

    if needs_consent and not payload.parent_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent email required for users under the consent threshold",
        )
    if not needs_consent and not payload.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email required for self-managed accounts",
        )

    now = datetime.now(UTC)
    user = User(
        email=payload.email,
        username=payload.username,
        password_hash=hash_password(payload.password),
        dob=payload.dob,
        country_code=payload.country_code,
        currency_code=payload.currency_code,
        topic_path=payload.topic_path,
        parent_email=str(payload.parent_email) if payload.parent_email else None,
        is_active=not needs_consent,
        policy_version_accepted=payload.policy_version_accepted,
        policy_accepted_at=now if payload.policy_version_accepted else None,
    )
    session.add(user)
    await session.flush()

    session.add(UserProgress(user_id=user.id))
    session.add(AuditLog(
        user_id=user.id,
        event_type="register",
        ip_address=request.client.host if request.client else None,
    ))

    if needs_consent:
        age = age_in_years(payload.dob, today)
        token = await issue_one_time_token(
            session, purpose=CONSENT_AUDIENCE,
            email=str(payload.parent_email), subject_id=user.id,
            expires_in=CONSENT_EXPIRY,
        )
        link = f"{settings.app_base_url}/consent/verify?token={token}"
        await get_email_sender().send(
            session, str(payload.parent_email), "consent_request",
            {
                "child_username": user.username,
                "age": age,
                "country_code": user.country_code,
                "link": link,
            },
        )
        await session.commit()
        return PendingConsentResponse(user_id=user.id)

    verify_token = await issue_one_time_token(
        session, purpose=VERIFY_EMAIL_AUDIENCE,
        email=str(payload.email), subject_id=user.id,
        expires_in=VERIFY_EMAIL_EXPIRY,
    )
    verify_link = f"{settings.app_base_url}/verify-email?token={verify_token}"
    await get_email_sender().send(
        session, str(payload.email), "verify_email",
        {"username": user.username, "link": verify_link},
    )

    secure = settings.environment != "development"
    _set_access_cookie(response, str(user.id), secure)
    await _issue_refresh_token(session, response, user.id, secure)
    _set_csrf_cookie(response, secure)
    await session.commit()
    await session.refresh(user)
    return user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py tests/test_register_consent.py -v`
Expected: ALL PASS (existing auth/consent tests + 3 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: register flow uses compliance resolver + self verify-email + policy capture"
```

---

### Task 8: Login by username-or-email

**Files:**
- Modify: `app/routers/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth.py`:

```python
async def test_login_with_username_for_emailless_account(client):
    # Underage account registered without child email, then parent-approved.
    from sqlalchemy import select
    from app.models.user import User
    from app.core.database import get_session
    from app.main import app

    reg = await client.post("/auth/register", json={
        "username": "emaillesskid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "parent2@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    assert reg.status_code == 201

    # Activate directly via the overridden session (simulating parent approval).
    gen = app.dependency_overrides[get_session]()
    db = await gen.__anext__()
    user = await db.scalar(select(User).where(User.username == "emaillesskid"))
    user.is_active = True
    await db.commit()

    resp = await client.post("/auth/login", json={
        "email": "emaillesskid", "password": "SecurePass123!",
    })
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth.py::test_login_with_username_for_emailless_account -v`
Expected: FAIL with 401 (login only matches by `User.email`).

- [ ] **Step 3: Implement identifier lookup**

In `app/routers/auth.py`, in `login()`, replace line 172:

```python
    user = await session.scalar(select(User).where(User.email == payload.email))
```

with:

```python
    ident = payload.email
    user = await session.scalar(
        select(User).where((User.email == ident) | (User.username == ident))
    )
```

(`select` and `User` are already imported in this module.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth.py -v`
Expected: ALL PASS (existing login tests still pass — they send an email value that still matches `User.email`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: login accepts username or email identifier"
```

---

### Task 9: Verify-email endpoints

**Files:**
- Modify: `app/routers/auth.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth.py`:

```python
async def test_verify_email_happy_path(client, db_session):
    from sqlalchemy import select
    from app.models.consent import SentEmail, OneTimeToken
    from app.models.user import User
    from app.services.tokens import VERIFY_EMAIL_AUDIENCE, issue_one_time_token, VERIFY_EMAIL_EXPIRY

    await client.post("/auth/register", json={
        "email": "verifyme@example.com", "username": "verifyme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "verifyme"))
    assert user.email_verified_at is None
    tok = await issue_one_time_token(
        db_session, purpose=VERIFY_EMAIL_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=VERIFY_EMAIL_EXPIRY,
    )
    resp = await client.get(f"/auth/verify-email?token={tok}")
    assert resp.status_code == 200
    await db_session.refresh(user)
    assert user.email_verified_at is not None


async def test_verify_email_bad_token_410(client):
    resp = await client.get("/auth/verify-email?token=not-a-real-token")
    assert resp.status_code == 410
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py::test_verify_email_happy_path tests/test_auth.py::test_verify_email_bad_token_410 -v`
Expected: FAIL with 404 (endpoint does not exist).

- [ ] **Step 3: Implement endpoints**

In `app/routers/auth.py`, add to the tokens import block the consume helper + exceptions, and import the user dependency. At the top of the file add:

```python
from app.services.tokens import (
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    consume_one_time_token,
)
```

(Add these names to the existing `from app.services.tokens import (...)` block rather than duplicating the import.)

Add these endpoints at the end of `app/routers/auth.py`:

```python
@router.get("/verify-email")
async def verify_email(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    from app.services.tokens import VERIFY_EMAIL_AUDIENCE
    try:
        row = await consume_one_time_token(session, token, VERIFY_EMAIL_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed) as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired") from exc
    user = await session.get(User, row.subject_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account not found")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
    await session.commit()
    return {"status": "ok"}


@router.post("/verify-email/resend")
@limiter.limit("3/hour")
async def resend_verify_email(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    from app.routers.users import get_current_user
    from app.services.tokens import VERIFY_EMAIL_AUDIENCE, VERIFY_EMAIL_EXPIRY
    user = await get_current_user(request, session)
    if user.email and user.email_verified_at is None:
        token = await issue_one_time_token(
            session, purpose=VERIFY_EMAIL_AUDIENCE, email=user.email,
            subject_id=user.id, expires_in=VERIFY_EMAIL_EXPIRY,
        )
        link = f"{settings.app_base_url}/verify-email?token={token}"
        await get_email_sender().send(
            session, user.email, "verify_email",
            {"username": user.username, "link": link},
        )
        await session.commit()
    return {"status": "accepted"}
```

(`get_current_user` is imported lazily inside the function to avoid a circular import between `app.routers.auth` and `app.routers.users`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py::test_verify_email_happy_path tests/test_auth.py::test_verify_email_bad_token_410 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: verify-email + resend endpoints"
```

---

### Task 10: Forgot-password / reset-password (age-split)

**Files:**
- Modify: `app/routers/auth.py`
- Modify: `app/core/csrf.py`
- Test: `tests/test_auth.py`, `tests/test_csrf.py` (regression only)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auth.py`:

```python
async def test_forgot_password_underage_routes_to_parent(client, db_session):
    from sqlalchemy import select
    from app.models.consent import SentEmail

    await client.post("/auth/register", json={
        "username": "fpkid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "fpparent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    resp = await client.post("/auth/forgot-password", json={"email": "fpkid"})
    assert resp.status_code == 202
    rows = (await db_session.scalars(
        select(SentEmail).where(SentEmail.template == "password_reset")
    )).all()
    assert any(r.to_email == "fpparent@example.com" for r in rows)


async def test_forgot_password_unknown_still_202(client):
    resp = await client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 202


async def test_reset_password_flow_revokes_refresh(client, db_session):
    from sqlalchemy import select
    from app.models.user import User, RefreshToken
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "resetme@example.com", "username": "resetme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "resetme"))
    tok = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
    )
    resp = await client.post("/auth/reset-password", json={
        "token": tok, "new_password": "BrandNewPass456!",
    })
    assert resp.status_code == 200
    rt = (await db_session.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )).all()
    assert all(t.revoked_at is not None for t in rt)
    login = await client.post("/auth/login", json={
        "email": "resetme@example.com", "password": "BrandNewPass456!",
    })
    assert login.status_code == 200


async def test_reset_password_weak_rejected(client, db_session):
    from sqlalchemy import select
    from app.models.user import User
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY, issue_one_time_token

    await client.post("/auth/register", json={
        "email": "weak@example.com", "username": "weakreset",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    user = await db_session.scalar(select(User).where(User.username == "weakreset"))
    tok = await issue_one_time_token(
        db_session, purpose=PASSWORD_RESET_AUDIENCE, email=user.email,
        subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
    )
    resp = await client.post("/auth/reset-password", json={
        "token": tok, "new_password": "short",
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -k "forgot_password or reset_password" -v`
Expected: FAIL (endpoints 404; also 403 CSRF until exempted).

- [ ] **Step 3: Add request schemas**

In `app/schemas/auth.py` add at the end:

```python
class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email", mode="before")
    @classmethod
    def normalise(cls, v: str) -> str:
        return v.lower().strip()


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v
```

- [ ] **Step 4: Implement endpoints**

In `app/routers/auth.py` add imports near the top (extend the existing schema import line 21):

```python
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    PendingConsentResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
```

Add these endpoints at the end of `app/routers/auth.py`:

```python
@router.post("/forgot-password", status_code=202)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.services.compliance import resolve_policy
    from app.services.tokens import PASSWORD_RESET_AUDIENCE, PASSWORD_RESET_EXPIRY
    ident = payload.email
    user = await session.scalar(
        select(User).where((User.email == ident) | (User.username == ident))
    )
    if user and user.is_active and user.deleted_at is None:
        today = date.today()
        policy = resolve_policy(user.country_code, user.dob, today)
        if policy.password_reset_mode == "parent":
            recipient = user.parent_email
        else:
            recipient = user.email
        if recipient:
            token = await issue_one_time_token(
                session, purpose=PASSWORD_RESET_AUDIENCE, email=recipient,
                subject_id=user.id, expires_in=PASSWORD_RESET_EXPIRY,
            )
            link = f"{settings.app_base_url}/reset-password?token={token}"
            await get_email_sender().send(
                session, recipient, "password_reset", {"link": link},
            )
            await session.commit()
    return {"status": "accepted"}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    from app.models.user import RefreshToken
    from app.services.tokens import PASSWORD_RESET_AUDIENCE
    try:
        row = await consume_one_time_token(session, payload.token, PASSWORD_RESET_AUDIENCE)
    except (TokenInvalid, TokenExpired, TokenAlreadyUsed) as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Link invalid or expired") from exc
    user = await session.get(User, row.subject_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account not found")
    user.password_hash = hash_password(payload.new_password)
    user.failed_login_count = 0
    user.locked_until = None
    now = datetime.now(UTC)
    tokens = await session.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    )
    for t in tokens:
        t.revoked_at = now
    await session.commit()
    return {"status": "ok"}
```

- [ ] **Step 5: Exempt the pre-auth POSTs from CSRF**

In `app/core/csrf.py`, add the two paths to `_DEFAULT_EXEMPT_PATHS` (lines 26–31):

```python
_DEFAULT_EXEMPT_PATHS = frozenset({
    "/auth/login", "/auth/register", "/health",
    "/auth/forgot-password", "/auth/reset-password",
    "/consent/decide",
    "/parent/auth/request",
    "/tutor/chat",
})
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -k "forgot_password or reset_password" -v && python -m pytest tests/test_csrf.py -v`
Expected: ALL PASS (4 new pass; CSRF regression suite still green).

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/auth.py backend/app/schemas/auth.py backend/app/core/csrf.py backend/tests/test_auth.py
git commit -m "feat: age-split forgot/reset password endpoints"
```

---

### Task 11: Retention purge service + CLI

**Files:**
- Create: `app/services/retention.py`
- Create: `app/cli.py`
- Test: `tests/test_retention.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_retention.py`:

```python
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.retention import purge_expired_accounts

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_purge_overwrites_pii_after_retention(db_session):
    old = datetime.now(UTC) - timedelta(days=40)
    u = User(
        email="purge@example.com", username="purgeme", password_hash="hash",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
        parent_email="pp@example.com", topic_path="core",
        is_active=False, deleted_at=old, deletion_requested_at=old,
    )
    db_session.add(u)
    await db_session.flush()

    n = await purge_expired_accounts(db_session, date.today())
    assert n == 1
    await db_session.refresh(u)
    assert u.purged_at is not None
    assert u.email is None
    assert u.parent_email is None
    assert u.topic_path is None
    assert u.username.startswith("purged_")
    assert u.password_hash == ""

    # Idempotent: second run does nothing.
    n2 = await purge_expired_accounts(db_session, date.today())
    assert n2 == 0


async def test_purge_skips_recent_deletions(db_session):
    recent = datetime.now(UTC) - timedelta(days=5)
    u = User(
        email="keep@example.com", username="keepme", password_hash="hash",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
        is_active=False, deleted_at=recent,
    )
    db_session.add(u)
    await db_session.flush()
    n = await purge_expired_accounts(db_session, date.today())
    assert n == 0
    await db_session.refresh(u)
    assert u.email == "keep@example.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_retention.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.retention'`.

- [ ] **Step 3: Implement the service**

Create `app/services/retention.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User


async def purge_expired_accounts(session: AsyncSession, today: date) -> int:
    """Hard-overwrite PII for accounts soft-deleted past the retention window.

    Idempotent: rows already purged (purged_at set) are skipped.
    Returns the number of rows purged.
    """
    cutoff = datetime.now(UTC) - timedelta(days=settings.data_retention_days)
    rows = (await session.scalars(
        select(User)
        .where(
            User.deleted_at.is_not(None),
            User.deleted_at < cutoff,
            User.purged_at.is_(None),
        )
        .execution_options(include_deleted=True)
    )).all()
    now = datetime.now(UTC)
    for u in rows:
        u.email = None
        u.username = f"purged_{u.id}"
        u.password_hash = ""
        u.parent_email = None
        u.topic_path = None
        u.purged_at = now
    await session.commit()
    return len(rows)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_retention.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Add the CLI test**

Append to `tests/test_retention.py`:

```python
async def test_cli_purge_command_runs(db_session, monkeypatch):
    import app.cli as cli

    async def fake_session_ctx():
        yield db_session

    monkeypatch.setattr(cli, "_session_scope", fake_session_ctx)
    code = await cli.run(["purge-accounts"])
    assert code == 0
```

- [ ] **Step 6: Run CLI test to verify it fails**

Run: `python -m pytest tests/test_retention.py::test_cli_purge_command_runs -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.cli'`.

- [ ] **Step 7: Implement the CLI**

Create `app/cli.py`:

```python
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from datetime import date

from app.core.database import AsyncSessionLocal
from app.services.retention import purge_expired_accounts


async def _session_scope() -> AsyncIterator:
    async with AsyncSessionLocal() as session:
        yield session


async def run(argv: list[str]) -> int:
    if not argv or argv[0] != "purge-accounts":
        print("usage: python -m app.cli purge-accounts", file=sys.stderr)
        return 2
    gen = _session_scope()
    session = await gen.__anext__()
    try:
        n = await purge_expired_accounts(session, date.today())
        print(f"purged {n} account(s)")
        return 0
    finally:
        await gen.aclose()


def main() -> None:
    raise SystemExit(asyncio.run(run(sys.argv[1:])))


if __name__ == "__main__":
    main()
```

Note: confirm the session factory name. Run `grep -n "AsyncSessionLocal\|async_session\|sessionmaker" app/core/database.py`. If the exported factory has a different name (e.g. `async_session_maker`), use that name in both the `from app.core.database import ...` line and the `async with ...` call.

- [ ] **Step 8: Run CLI test to verify it passes**

Run: `python -m pytest tests/test_retention.py -v`
Expected: ALL PASS (3 passed).

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/retention.py backend/app/cli.py backend/tests/test_retention.py
git commit -m "feat: data-retention purge service + CLI command"
```

---

### Task 12: GDPR export — service + self endpoint

**Files:**
- Create: `app/services/export_service.py`
- Modify: `app/routers/users.py`
- Test: `tests/test_users.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_users.py`:

```python
async def test_self_export_returns_profile_json(client, db_session):
    await client.post("/auth/register", json={
        "email": "export@example.com", "username": "exportme",
        "password": "SecurePass123!", "dob": "2009-01-01",
        "country_code": "GB", "currency_code": "GBP",
        "policy_version_accepted": "2026-05-16",
    })
    # Register set auth cookies on the client.
    resp = await client.get("/users/me/export")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"].startswith("attachment")
    data = resp.json()
    assert data["profile"]["username"] == "exportme"
    assert data["profile"]["email"] == "export@example.com"
    assert "progress" in data
    assert "consent" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_users.py::test_self_export_returns_profile_json -v`
Expected: FAIL with 404.

- [ ] **Step 3: Implement the export service**

Create `app/services/export_service.py`:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import SentEmail
from app.models.user import User, UserProgress


async def build_user_export(session: AsyncSession, user: User) -> dict[str, Any]:
    progress = await session.get(UserProgress, user.id)
    emails = (await session.scalars(
        select(SentEmail).where(
            (SentEmail.to_email == user.email)
            | (SentEmail.to_email == user.parent_email)
        )
    )).all()
    return {
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "dob": user.dob.isoformat(),
            "country_code": user.country_code,
            "currency_code": user.currency_code,
            "topic_path": user.topic_path,
            "parent_email": user.parent_email,
            "created_at": user.created_at.isoformat(),
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "policy_version_accepted": user.policy_version_accepted,
            "policy_accepted_at": user.policy_accepted_at.isoformat() if user.policy_accepted_at else None,
            "profiling_enabled": user.profiling_enabled,
            "marketing_opt_in": user.marketing_opt_in,
        },
        "progress": {
            "xp": progress.xp if progress else 0,
            "level": progress.level if progress else 1,
            "streak_count": progress.streak_count if progress else 0,
        },
        "consent": {
            "parent_consent_given_at": user.parent_consent_given_at.isoformat() if user.parent_consent_given_at else None,
            "consent_declined_at": user.consent_declined_at.isoformat() if user.consent_declined_at else None,
        },
        "emails": [
            {"template": e.template, "to": e.to_email} for e in emails
        ],
    }
```

- [ ] **Step 4: Implement the self endpoint**

In `app/routers/users.py` add imports at the top:

```python
from fastapi.responses import JSONResponse

from app.services.export_service import build_user_export
```

Add this endpoint at the end of `app/routers/users.py`:

```python
@router.get("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    data = await build_user_export(session, current_user)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="invest-ed-export.json"'},
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_users.py::test_self_export_returns_profile_json -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/export_service.py backend/app/routers/users.py backend/tests/test_users.py
git commit -m "feat: GDPR self-service data export"
```

---

### Task 13: GDPR export — parent endpoint

**Files:**
- Modify: `app/routers/parent.py`
- Test: `tests/test_parent_dashboard.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_parent_dashboard.py`. (Inspect the top of `tests/test_parent_dashboard.py` first for the existing parent-login helper; reuse whatever helper logs a parent in and returns the parent-session cookie. The skeleton below names it `_parent_session`; replace with the file's actual helper.)

```python
async def test_parent_export_child(client, db_session):
    from sqlalchemy import select
    from app.models.user import User

    # Underage child with a parent.
    await client.post("/auth/register", json={
        "username": "pexkid", "password": "SecurePass123!",
        "dob": "2016-01-01", "country_code": "GB", "currency_code": "GBP",
        "parent_email": "pexparent@example.com",
        "policy_version_accepted": "2026-05-16",
    })
    child = await db_session.scalar(select(User).where(User.username == "pexkid"))

    cookies = await _parent_session(client, db_session, "pexparent@example.com")
    resp = await client.get(
        f"/parent/children/{child.id}/export", cookies=cookies
    )
    assert resp.status_code == 200
    assert resp.json()["profile"]["username"] == "pexkid"


async def test_parent_export_not_owned_404(client, db_session):
    import uuid
    cookies = await _parent_session(client, db_session, "stranger@example.com")
    resp = await client.get(
        f"/parent/children/{uuid.uuid4()}/export", cookies=cookies
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_parent_dashboard.py -k parent_export -v`
Expected: FAIL with 404 (endpoint does not exist).

- [ ] **Step 3: Implement the endpoint**

In `app/routers/parent.py` add import at the top:

```python
from app.services.export_service import build_user_export
```

Add this endpoint at the end of `app/routers/parent.py`:

```python
@router.get("/children/{user_id}/export")
async def export_child_data(
    user_id: uuid.UUID,
    parent_email: str = Depends(get_current_parent),
    session: AsyncSession = Depends(get_session),
):
    child = await _get_owned_child(session, parent_email, user_id)
    if child.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Account deleted")
    from fastapi.responses import JSONResponse
    data = await build_user_export(session, child)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": 'attachment; filename="invest-ed-child-export.json"'},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_parent_dashboard.py -k parent_export -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/parent.py backend/tests/test_parent_dashboard.py
git commit -m "feat: parent-initiated GDPR export for child accounts"
```

---

### Task 14: High-privacy default — gate personalisation on profiling_enabled

**Files:**
- Modify: `app/services/recommendation_service.py` (verify exact name first)
- Test: `tests/test_recommendation_service.py`

- [ ] **Step 1: Inspect the personalisation entry point**

Run: `grep -n "def .*recommend\|def .*next\|profiling" app/services/recommendation_service.py | head`
Identify the public function that returns personalised recommendations and the parameter that carries the `User` (or `user_id`). The step below assumes a function `recommend_next(...)` that receives a `User`. Adapt names to what you find; do not invent a different module.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_recommendation_service.py`:

```python
async def test_recommendations_empty_when_profiling_disabled(db_session):
    """High-privacy default: personalised recommendations are withheld
    unless the user has explicitly enabled profiling."""
    from datetime import date
    from app.models.user import User
    from app.services.recommendation_service import recommend_next

    u = User(
        email="np@example.com", username="noprofile", password_hash="x",
        dob=date(2010, 1, 1), country_code="GB", currency_code="GBP",
        profiling_enabled=False,
    )
    db_session.add(u)
    await db_session.flush()
    result = await recommend_next(db_session, u)
    assert result == [] or result is None
```

(If `recommend_next` is synchronous or has a different signature, mirror the file's existing test style for calling it — check the other tests in `tests/test_recommendation_service.py`.)

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_recommendation_service.py::test_recommendations_empty_when_profiling_disabled -v`
Expected: FAIL (current code returns recommendations regardless of `profiling_enabled`).

- [ ] **Step 4: Implement the guard**

At the very top of the public recommendation function body (before any computation), add:

```python
    if not getattr(user, "profiling_enabled", False):
        return []
```

If the function returns `None` for "no recommendations" elsewhere, return `None` instead of `[]` to stay consistent with the file's existing contract — match what the other code paths/tests in that module expect.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_recommendation_service.py -v`
Expected: ALL PASS. If pre-existing tests in this file assumed recommendations without setting `profiling_enabled`, update those test fixtures to set `profiling_enabled=True` (they are testing the recommendation algorithm, not the privacy gate) and note this in the commit message.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommendation_service.py backend/tests/test_recommendation_service.py
git commit -m "feat: gate personalised recommendations on profiling_enabled (high-privacy default)"
```

---

### Task 15: Compliance docs + seed accounts

**Files:**
- Create: `docs/compliance/DPIA.md`
- Create: `docs/compliance/privacy-notice.md`
- Create: `docs/compliance/operations.md`
- Create: `backend/app/seed/compliance_accounts.py`
- Test: `tests/test_seed.py` (add one test)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_seed.py`:

```python
async def test_compliance_accounts_seed_idempotent(db_session):
    from sqlalchemy import func, select
    from app.models.user import User
    from app.seed.compliance_accounts import seed_compliance_accounts

    await seed_compliance_accounts(db_session)
    await seed_compliance_accounts(db_session)  # second run must not duplicate
    count = await db_session.scalar(
        select(func.count()).select_from(User).where(
            User.username.in_([
                "pending_consent_kid", "consented_kid", "selfteen",
            ])
        )
    )
    assert count == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_seed.py::test_compliance_accounts_seed_idempotent -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.seed.compliance_accounts'`.

- [ ] **Step 3: Implement the seed module**

Create `backend/app/seed/compliance_accounts.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserProgress

_PASSWORD = "TestPassword1234!"


async def _ensure(session: AsyncSession, **kwargs) -> bool:
    existing = await session.scalar(
        select(User).where(User.username == kwargs["username"])
    )
    if existing:
        return False
    user = User(password_hash=hash_password(_PASSWORD), **kwargs)
    session.add(user)
    await session.flush()
    session.add(UserProgress(user_id=user.id))
    return True


async def seed_compliance_accounts(session: AsyncSession) -> None:
    if settings.environment == "production":
        return
    now = datetime.now(UTC)
    await _ensure(
        session,
        email=None, username="pending_consent_kid",
        dob=date(2016, 1, 1), country_code="GB", currency_code="GBP",
        parent_email="parent@test.invest-ed", is_active=False,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email=None, username="consented_kid",
        dob=date(2016, 1, 1), country_code="GB", currency_code="GBP",
        parent_email="parent@test.invest-ed", is_active=True,
        parent_consent_given_at=now,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await _ensure(
        session,
        email="selfteen@test.invest-ed", username="selfteen",
        dob=date(2009, 1, 1), country_code="GB", currency_code="GBP",
        is_active=True, email_verified_at=None,
        policy_version_accepted=settings.privacy_notice_version,
        policy_accepted_at=now,
    )
    await session.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_seed.py::test_compliance_accounts_seed_idempotent -v`
Expected: PASS.

- [ ] **Step 5: Write the compliance docs**

Create `docs/compliance/DPIA.md` with these sections (write real prose, not placeholders): **Scope** (Invest-Ed, children 8+, jurisdictions resolved by country_code); **Data inventory** (table: field → purpose → lawful basis → retention — list every `users` column from `app/models/user.py`); **Lawful basis per regime** (UK-AADC/UK-GDPR: parental consent < 13, legitimate interest for core education; COPPA: verifiable parental consent < 13 via parent-email gate; EU GDPR-K: consent 13/16 by member state; HK PDPO: PDPO principles); **Children-specific risks & mitigations** (self-declared age → mitigation: parental-email gate + DOB plausibility 8–120; profiling → mitigation: off by default per Task 14; gamification streaks → retained as standard educational mechanic, reviewed as non-detrimental; data minimisation → child email optional when parent present); **Retention** (30 days post soft-delete then hard purge, Task 11); **Subject rights** (export Task 12/13, erasure existing parent endpoint); **Residual risks & backlog** (verifiable parental consent stronger than email for strict COPPA — future; cookie/analytics consent — only if analytics added).

Create `docs/compliance/privacy-notice.md` — the child-friendly notice source of truth: short plain-language sections "What we collect", "Why", "Who can see it", "How long we keep it", "Your choices (ask a grown-up)", "Contact". Reading age ~8–12, no dark patterns. Note that the frontend signup copy must be derived from this file and the version string equals `settings.privacy_notice_version` (`2026-05-16`).

Create `docs/compliance/operations.md` — the purge runbook: command `cd invest-ed/backend && python -m app.cli purge-accounts`; recommended schedule (daily, e.g. cron `15 3 * * *`); what it does (overwrites PII for accounts soft-deleted > `data_retention_days`); idempotent and safe to re-run; how to verify (`SELECT count(*) FROM users WHERE deleted_at IS NOT NULL AND purged_at IS NULL AND deleted_at < now() - interval '30 days'` should be 0 after a run).

- [ ] **Step 6: Commit**

```bash
git add backend/app/seed/compliance_accounts.py backend/tests/test_seed.py docs/compliance/
git commit -m "feat: compliance seed accounts + DPIA, privacy notice, operations docs"
```

---

### Task 16: Frontend — privacy acknowledgement, forgot/reset/verify pages, verify banner

**Files:**
- Modify: `frontend/src/pages/child/Signup.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/ForgotPassword.tsx`
- Create: `frontend/src/pages/ResetPassword.tsx`
- Create: `frontend/src/pages/VerifyEmail.tsx`
- Create: `frontend/src/components/VerifyEmailBanner.tsx`
- Modify: the login page (find it: `grep -rn "auth/login\|Sign in" frontend/src/pages | head`)
- Modify: `frontend/src/api/*` (find the auth API module: `grep -rn "auth/register\|auth/login" frontend/src/api`)

- [ ] **Step 1: Inspect existing frontend auth wiring**

Run: `grep -rn "auth/register\|auth/login\|apiFetch\|API_BASE" frontend/src/api/*.ts | head -20` and open the auth API module + `frontend/src/pages/child/Signup.tsx` and the login page. Mirror their existing fetch helper, error handling, and styling (Tailwind, amber theme). Do not introduce a new HTTP client.

- [ ] **Step 2: Add privacy acknowledgement to Signup**

In `frontend/src/pages/child/Signup.tsx`:
- Add a required, initially-unchecked checkbox before the submit button:
  ```tsx
  <label className="flex items-start gap-2 text-sm text-gray-700">
    <input
      type="checkbox"
      checked={policyAccepted}
      onChange={(e) => setPolicyAccepted(e.target.checked)}
      className="mt-1"
    />
    <span>
      I (or my grown-up) have read the{' '}
      <a href="/privacy" className="underline text-amber-700">privacy notice</a>.
    </span>
  </label>
  ```
- Add `const [policyAccepted, setPolicyAccepted] = useState(false);`
- Disable submit unless `policyAccepted` is true.
- Include `policy_version_accepted: "2026-05-16"` in the register request body when `policyAccepted` (use the same constant the backend uses; hardcode the string here — there is no shared config).

- [ ] **Step 3: Create ForgotPassword page**

Create `frontend/src/pages/ForgotPassword.tsx`: a single email/username input + submit that POSTs `{ email }` to `/auth/forgot-password` using the existing fetch helper, then always shows a neutral confirmation ("If that account exists, we've sent a reset link") regardless of response (the endpoint always 202s). Match existing page styling.

- [ ] **Step 4: Create ResetPassword page**

Create `frontend/src/pages/ResetPassword.tsx`: read `token` from `?token=` (use the router's existing query mechanism — check how `ConsentVerify.tsx` reads its token and copy that pattern). Form: new password + confirm. On submit POST `{ token, new_password }` to `/auth/reset-password`. On 200 → success message + link to login. On 410 → "link expired" message. On 422 → show the password-rule validation error.

- [ ] **Step 5: Create VerifyEmail page**

Create `frontend/src/pages/VerifyEmail.tsx`: read `token` from query, on mount GET `/auth/verify-email?token=...`, show success or "link invalid/expired" (410) with a button that POSTs `/auth/verify-email/resend` (only meaningful if logged in).

- [ ] **Step 6: Create VerifyEmailBanner**

Create `frontend/src/components/VerifyEmailBanner.tsx`: a dismissible amber banner shown when the logged-in user's profile has `email` set and is unverified. Determine verified state from the profile endpoint — check `GET /users/me` (`frontend/src/api`); if the profile response does not yet expose `email_verified_at`, add it to the `UserProfile` schema/response in `backend/app/schemas/user.py` and `app/routers/users.py` `get_profile` (it returns the ORM `User`, so exposing the field on `UserProfile` is sufficient — add `email_verified_at: datetime | None = None` to the `UserProfile` pydantic model). Render the banner in the authenticated shell/layout component (find it: `grep -rn "Outlet\|Shell\|Layout" frontend/src --include=*.tsx | head`).

- [ ] **Step 7: Wire routes + login link**

In `frontend/src/App.tsx` add public routes:
```tsx
<Route path="/forgot-password" element={<ForgotPassword />} />
<Route path="/reset-password" element={<ResetPassword />} />
<Route path="/verify-email" element={<VerifyEmail />} />
```
On the login page, add a `<Link to="/forgot-password">Forgot password?</Link>` under the password field, styled like existing secondary links.

- [ ] **Step 8: Type-check and build**

Run:
```bash
cd invest-ed/frontend && npx tsc --noEmit && npm run build
```
Expected: no TypeScript errors; build succeeds.

- [ ] **Step 9: Manual smoke (golden path)**

With backend running (`cd invest-ed/backend && uvicorn app.main:app --port 8000`) and frontend (`cd invest-ed/frontend && npm run dev`):
- Register a teen (DOB making age ≥13, GB) with the privacy box ticked → confirm a `verify_email` row appears in `sent_emails` (query DB) and the verify banner shows after login.
- Use "Forgot password?" with the teen's email → confirm a `password_reset` row appears in `sent_emails`.
- Open the reset link's token via `/reset-password?token=...` (copy token from the `sent_emails.body`), set a new password, log in with it.
Report results explicitly; if the UI cannot be exercised, say so rather than claiming success.

- [ ] **Step 10: Commit**

```bash
git add invest-ed/frontend backend/app/schemas/user.py backend/app/routers/users.py
git commit -m "feat: frontend privacy ack, forgot/reset/verify pages, verify banner"
```

---

### Task 17: Full regression + final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire backend suite**

Run: `cd invest-ed/backend && python -m pytest`
Expected: ALL PASS (existing suite + all new tests). Investigate and fix any failure before proceeding — do not mark complete with failures.

- [ ] **Step 2: Lint**

Run: `cd invest-ed/backend && ruff check .`
Expected: `All checks passed!`. Fix any findings (prefer `ruff check --fix` for import ordering; hand-fix logic issues).

- [ ] **Step 3: Confirm no stale flat consent logic remains**

Run: `grep -rn "16 if .* else 13\|EU_COUNTRIES_16" app/ | grep -v compliance.py | grep -v consent_service.py`
Expected: no results (jurisdiction logic lives only in `compliance.py`; `consent_service.py` keeps the back-compat alias only).

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -A backend
git commit -m "chore: lint + regression fixes for compliance/auth sub-project"
```

(Skip this commit if there were no changes.)

---

## Self-Review

**1. Spec coverage**

| Spec section | Task(s) |
|---|---|
| §1 Compliance policy core | 1, 2 |
| §2 Email verification (parent-gated / self) | 3 (column), 5 (template), 7 (self send), 9 (endpoints), 16 (banner) |
| §3 Password reset (age-split) | 4 (tokens), 5 (template), 10 (endpoints), 16 (pages) |
| §4 Retention purge | 3 (`purged_at`), 11 |
| §4 GDPR export | 12 (self), 13 (parent) |
| §5 High-privacy defaults | 3 (`profiling_enabled`/`marketing_opt_in`), 14 |
| §5 Child-friendly notice + terms | 3 (`policy_*` cols), 4 (`privacy_notice_version`), 7 (capture), 15 (notice doc), 16 (UI ack) |
| §5 Data minimisation (optional child email, username login) | 3 (email nullable), 6 (schema), 7 (register), 8 (login) |
| §5 DPIA + privacy docs | 15 |
| §6 Compliance test accounts | 15 |
| Error handling (410/202/422) | 9, 10, 13 |
| Testing (unit + integration + regression) | every task + 17 |

No spec section is unimplemented.

**2. Placeholder scan:** No "TBD"/"implement later"/"add error handling" placeholders. Every code step contains complete code. Two tasks (11 step 7, 14, 16) instruct verifying an exact existing symbol name before editing — these include the exact `grep` to run and a named fallback, which is correct guidance, not a placeholder.

**3. Type consistency:** `CompliancePolicy` field names (`requires_parental_consent`, `email_verification_target`, `password_reset_mode`, `consent_age`, `data_retention_days`, `profiling_default_off`) are used identically in Tasks 1, 7, 10. `resolve_policy(country_code, dob, today)` signature is consistent across Tasks 1, 7, 10. Token constants `VERIFY_EMAIL_AUDIENCE/EXPIRY`, `PASSWORD_RESET_AUDIENCE/EXPIRY` defined in Task 4 and used unchanged in 7, 9, 10. `purge_expired_accounts(session, today)` signature consistent in Tasks 11 (def) and the CLI. `build_user_export(session, user)` consistent across Tasks 12 (def), 12 (self route), 13 (parent route). New `users` columns defined once in Task 3 and referenced by exact name everywhere after. Consistent.

Issues found during review: none requiring a new task. The `email`-nullable change (Task 3) is correctly paired with optional-email schema (Task 6), register guard (Task 7), and username login (Task 8), so no flow can break by a child lacking an email.
