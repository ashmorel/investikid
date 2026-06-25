# Security Policy

InvestiKid is a children's finance-education app, so we take security and
privacy seriously. Thank you for helping keep it — and its young users — safe.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report suspected vulnerabilities privately to **privacy@invest-ed.app**.
Include, where possible:

- a description of the issue and its impact,
- steps to reproduce (a proof-of-concept if you have one),
- affected URLs / endpoints / components, and
- any suggested remediation.

You can expect an acknowledgement within **5 business days**. We will keep you
updated on remediation progress and will credit reporters who wish to be
named once a fix has shipped.

Alternatively, you may use GitHub's **private vulnerability reporting**
("Report a vulnerability" under the Security tab) if it is enabled on this
repository.

## Scope

In scope:

- the web app at `app.investikid.ai`,
- the API at `api.investikid.ai`,
- the iOS and Android applications,
- the source code in this repository.

Out of scope: third-party services we rely on (Railway, Vercel, Stripe,
Apple/Google billing, Resend) — report those to the respective vendor.

## Responsible disclosure

Please give us a reasonable opportunity to investigate and remediate before any
public disclosure. Do not access, modify, or delete data that is not your own,
and do not run tests that could degrade the service for real users (no
load/DoS testing, no automated scanning against production).

## A note on this being a kids' app

We are bound by children's-privacy regulations (e.g. COPPA, the UK Children's
Code). Reports that touch children's personal data, consent flows, or the
parent–child trust model are treated as the highest priority.
