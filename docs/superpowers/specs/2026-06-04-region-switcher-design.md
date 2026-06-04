# Country/Region Content Switcher — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Context:** First feature after the "Yasmin's Choice" rebrand (SP-0/A/B/C/D1/D2/F shipped). Lets a child switch the country their learning content is geared toward (US / UK / Hong Kong key exchanges) to explore investing globally.

## Goal

Make it easy for a child to change their **learning region** so lesson modules + recommendations re-target US (NASDAQ/NYSE), UK (LSE), or Hong Kong (HKEX), with the practice-portfolio currency optionally following — without touching the child's legal/consent country.

## Key constraint discovered (load-bearing)

`country_code` currently does **double duty**: (a) content filtering (`module.country_codes` matching in `content.py` + `recommendation_service.py` + `analytics_service.py`) **and** (b) the **COPPA/UK-GDPR consent regime** (`compliance.py` / `consent_service.py` derive the parental-consent age from it). Therefore the region switch must **not** mutate `country_code`. We introduce a separate, decoupled field.

`PATCH /users/me` already accepts `country_code`/`currency_code`/`topic_path` (`PreferencesUpdate`); `Me`/`UserProfile` already return `country_code`/`currency_code`. The simulator Market already lists all three exchanges regardless of country.

## Data model

- New `User.content_region: str | None` (`String(2)`, nullable, default NULL). The child's chosen learning region. **NULL ⇒ fall back to `country_code`.** Hand-written chained Alembic migration (check `alembic heads` from `backend/` first).
- Effective region: a small helper `content_region_for(user) -> str` returning `user.content_region or user.country_code` (in `app/services/content_service.py` or a `User` property). Used everywhere content is region-gated.
- **`country_code` is never written by this feature** — consent/compliance keep using it unchanged.
- Supported regions (validated set): **`US`, `GB`, `HK`**, mapped to currencies **USD / GBP / HKD**.

## Backend

- **Region-gating swap:** in `content.py` (the two `country_ok` checks), `recommendation_service.py` (lines ~60 + ~404), and `analytics_service.py` — replace `current_user.country_code` / `user.country_code` (where used for `module.country_codes` matching) with `content_region_for(user)`. **Do not** change `compliance.py` / `consent_service.py` (they keep `country_code`).
- **`PATCH /users/me`** (`users.py` + `PreferencesUpdate` in `schemas/user.py`): accept optional `content_region`; validate it ∈ `{US, GB, HK}` (reuse/mirror the ISO-2 validator style; reject others with 422). `currency_code` already accepted (FE sends it on the confirmed currency switch).
- **Responses:** add `content_region: str | None` to `UserProfile` (`schemas/user.py`) and the `Me` schema (`schemas/auth.py`) so the UI knows the current region.
- **Region→currency map** lives as a backend constant for validation reference and a matching frontend constant for the UI (US→USD, GB→GBP, HK→HKD).

## Frontend

- **`RegionSwitcher`** component (`src/components/child/`): an accessible, labelled control (segmented buttons or a `<select>`) showing **🇺🇸 US · 🇬🇧 UK · 🇭🇰 HK**, current region highlighted (`aria-current`/`aria-pressed`); emoji flags `aria-hidden`, real text labels. On change:
  1. `parent…`/`authApi.updatePreferences({ content_region })` (the existing `PATCH /users/me` client) → on success invalidate `['modules']`, `['recommendations']`, `['module-levels']`/`['level-lessons']`, and `['me']` queries so content re-filters live.
  2. If the region's currency ≠ the user's current `currency_code`, show a small confirm ("Also switch your practice money to **HK$**?"). On yes → `updatePreferences({ currency_code })` + invalidate `['portfolio']`/`['portfolio-history']` (holdings persist; total re-displays converted). On no → leave currency.
- **Placement:** in the existing child **`ProfileMenu`** (persistent settings home) **and** a compact switcher on the **Quests/Learn** screen header (discoverable where region-affected modules live). Both render the same `RegionSwitcher`.
- Read the current region from the `me` query (`content_region ?? country_code`).

## Scope of effect

In: lesson **modules** (Quests/Lessons) + **recommendations** (Home) re-filter by region; optional practice-**currency** switch. The **simulator stays global** (all exchanges shown) — only currency follows. Out: reordering/featuring the region's exchange in the simulator (nice-to-have, later); no change to consent, auth, or the legal country.

## Accessibility & safety

- COPPA: legal `country_code` untouched → no consent-regime change; region/currency are low-risk so the child may change them.
- WCAG 2.2 AA: the switcher is a real labelled control with visible focus + current-state indication; the currency confirm is an accessible dialog; `vitest-axe` on new UI. iOS ≥16px; no `maximum-scale`.

## Testing

- **Backend:** `content_region_for` fallback (NULL→country_code, set→used); content/recommendation filtering uses the effective region (a US child with `content_region='HK'` sees HK modules, not US); `PATCH /users/me` accepts `US/GB/HK` + rejects others (422) + never alters `country_code`; `compliance`/consent still keyed on `country_code`; migration applies (check head). Async tests use the `client`/`db_session` fixtures + `loop_scope="session"`.
- **Frontend:** `RegionSwitcher` renders the 3 options + current highlight + axe; selecting calls `updatePreferences({content_region})` + invalidates; the currency-confirm flow (yes → currency PATCH, no → not); both placements render it.
- `tsc -b`, lint, test, build; backend `ruff` + `pytest`. All CI jobs green.

## Plan shape
Backend-first: T1 `content_region` field + migration + `content_region_for` helper → T2 wire region-gating (content/recommendation/analytics) + tests → T3 `PATCH`/schemas/responses (content_region + validation) + tests → T4 FE `RegionSwitcher` + API + currency map (+ tests) → T5 mount in ProfileMenu + Quests header + query invalidation + currency confirm → T6 regression + push. Each green-CI.

## Decisions captured
Separate persistent `content_region` (legal `country_code` untouched) · regions US/GB/HK · region switch offers a currency switch (portfolio persists) · affects modules + recommendations; simulator stays all-exchanges · child-changeable · placed in ProfileMenu + Quests header.
