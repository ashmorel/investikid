# Test-Account / Tier Matrix

This document lists all seeded developer and test accounts available in non-production environments. Every account uses the password `TestPassword1234!`. Neither seeder runs when `settings.environment == "production"` — these accounts must never exist in production.

## Account Matrix

| Username | Email | Tier / Role | Parent email | Purpose / what to test |
|---|---|---|---|---|
| `tier_parent` | `tier-parent@test.invest-ed` | Adult / parent, active, email verified | — | Parent dashboard flows; premium toggle via `POST /parent/children/{id}/premium`; viewing child accounts; owns both tier children below |
| `premium_child` | `premium-child@test.invest-ed` | Child, `is_premium=True`, active, parent-consented | `tier-parent@test.invest-ed` | Full premium experience: premium modules unlocked ("What is Crypto?", "Revenue, Costs & Profit"), premium gamification challenge ("Market Explorer"), higher AI-tutor message limit, premium LLM tier, premium-only stock tickers, Premium UI badge |
| `free_child` | `free-child@test.invest-ed` | Child, `is_premium=False`, active, parent-consented | `tier-parent@test.invest-ed` | Free-tier experience: premium modules appear in locked state, no premium badge, standard AI-tutor message limit, standard LLM tier, no premium stock tickers; use to verify tier gating end-to-end |
| `pending_consent_kid` | *(none)* | Child, `is_active=False`, awaiting parent consent | `parent@test.invest-ed` | Pre-consent state: account exists but cannot log in; tests the consent-pending UI and any blocked-access enforcement |
| `consented_kid` | *(none)* | Child, `is_active=True`, parent consent given | `parent@test.invest-ed` | Post-consent child without an email address; tests flows for email-less child accounts once consent is recorded |
| `selfteen` | `selfteen@test.invest-ed` | Teen self-account, `is_active=True`, email **not** verified (`email_verified_at=None`) | — | Teen self-registration path with unverified email; tests email-verification prompts, access restrictions before verification, and the age-band where no parental consent is required |

## How to Seed

Run the combined seed from the backend directory:

```bash
cd invest-ed/backend
python -m app.seed.run
```

This command is idempotent — running it multiple times will not create duplicate accounts or overwrite existing data. It is automatically skipped in production environments. The run includes the content seed, gamification seed, and `seed_tier_accounts` (from `app/seed/tier_accounts.py`).

The compliance accounts (`pending_consent_kid`, `consented_kid`, `selfteen`) are created by `seed_compliance_accounts` in `app/seed/compliance_accounts.py`. That function is invoked directly in the test suite fixtures rather than via `app.seed.run`, but the accounts are documented here for completeness. To seed them manually in a local dev environment, call `seed_compliance_accounts` from a one-off script or add it to `app.seed.run` locally.

## Granting Premium Ad Hoc

To grant premium status to any existing account outside of seeding:

```bash
cd invest-ed/backend
python -m app.cli grant-premium <email|username>
```

To revoke premium:

```bash
python -m app.cli grant-premium <email|username> --revoke
```

The in-app path for a logged-in parent is the premium toggle on the parent dashboard, which calls `POST /parent/children/{id}/premium`. Use `tier_parent` to exercise that endpoint with `premium_child` or `free_child`.

## What Differs by Tier

| Feature | Free (`free_child`) | Premium (`premium_child`) |
|---|---|---|
| Sample premium modules ("What is Crypto?", "Revenue, Costs & Profit") | Locked state | Unlocked |
| Premium gamification challenge ("Market Explorer") | Not accessible | Accessible |
| AI-tutor message limit | Standard (lower) | Higher |
| LLM tier for AI tutor | Standard | Premium |
| Premium-only stock tickers | Not shown | Available |
| UI badge | None | "Premium" badge displayed |

Use `free_child` and `premium_child` side-by-side to confirm all of the above gates behave correctly on both the API and UI layers.

## Security Note

Both `app/seed/tier_accounts.py` and `app/seed/compliance_accounts.py` guard their execution with:

```python
if settings.environment == "production":
    return
```

These accounts must never be created in production. The password `TestPassword1234!` is a well-known test credential; any deployment pipeline or environment check should confirm `environment != "production"` before running seeds. If a production database is ever found to contain any of these usernames or emails, treat it as a data integrity incident and remove the accounts immediately.
