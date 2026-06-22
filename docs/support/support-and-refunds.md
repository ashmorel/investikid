# Support & Refunds Procedures

**Purpose:** How to handle the common inbound requests once real users (and paying parents) are on board. It's a kids' app, so most accounts are parent-managed.

**Contact:** support requests arrive at the published address (see `docs/compliance/privacy-notice.md`). Outbound app email currently sends from `noreply@invest-ed.app` (`backend/app/core/config.py: email_from`) — see the email-domain migration note in the pre-TestFlight checklist.

## Account & login
| Request | What to do |
|---|---|
| Can't log in (web) | Confirm same-site login is healthy (runbook). Offer password reset (`/auth/forgot-password`) / magic-link. Persistent login auto-refreshes for ~30 days. |
| Forgot password | User triggers reset from the login screen; a reset email is sent. We never set passwords for them. |
| Biometric won't work | It's per-device and OS-enforced; re-enrolling Face ID/fingerprint invalidates the stored secret by design. Have them sign in with email/password, then re-enable biometric. |
| Parent can't see child progress | Confirm the parent–child link (household) and that the parent is signed into the parent account; the Mastery Report is on the parent dashboard. |

## Subscriptions & refunds
**Where the purchase was made determines who refunds it** — we cannot refund a store purchase on the store's behalf.
| Purchased via | Refund owner | Our action |
|---|---|---|
| **Apple (in-app)** | Apple | Direct the user to **reportaproblem.apple.com**. We can confirm entitlement status; Apple processes the refund. |
| **Google Play (in-app)** | Google | Direct to Play → Order history → Request refund (or Google support). We confirm status only. |
| **Stripe (web)** | Us | We can refund via the Stripe Dashboard (operator action — requires Stripe access; **not** done by Claude). Then entitlement is revoked at next reconcile. |

- **Plans:** monthly + annual (`plan_catalog.py`; real prices live in Stripe/App Store/Play, operator-managed).
- **Entitlement looks wrong after purchase/refund:** the daily `subscriptions/reconcile` cron re-pulls authoritative provider state and self-heals. To force it, re-run the cron (runbook). Free users get **one** market; premium unlocks all.
- **Cancellations:** users cancel through the store they bought from (Apple/Google) or, for Stripe, via the billing portal. Access continues until period end.

## Data & privacy (kids' app — handle promptly)
| Request | What to do |
|---|---|
| Delete my / my child's account | Honour it. Deletion triggers the two-phase erasure (soft-delete → hard purge after 30 days; see `docs/compliance/operations.md`). Biometric secrets are device-local and revoked on deletion. |
| Access / correct my data | Subject rights are covered in `docs/compliance/DPIA.md` §6. Route to the operator; do not export PII ad-hoc. |
| Parental consent issues (under-13) | Account activates only after the parent clicks the consent email. Re-send if needed. |

## Escalate (don't resolve solo)
- Payment disputes/chargebacks → operator (Stripe/Apple/Google).
- Suspected safety issue with AI output or content → capture + escalate (runbook); tighten guardrails.
- Security report / suspected breach → security owner; see `docs/security/`.

## Gaps / TODO
- A ticketing tool + canned responses for the rows above.
- A public FAQ / help page linked from the app.
- Confirm the support mailbox + auto-acknowledgement once the email domain is finalised.
