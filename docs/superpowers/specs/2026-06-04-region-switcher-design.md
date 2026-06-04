# Country/Region Content Switcher — Design

**Status:** Draft for review.
**Date:** 2026-06-04
**Context:** First feature after the "Yasmin's Choice" rebrand (SP-0/A/B/C/D1/D2/F shipped). Lets a child switch the country their learning content is geared toward (US / UK / Hong Kong key exchanges) to explore investing globally.

## Goal

Give the child **two independent, easy-to-change preferences** so they can explore investing globally:
1. **Learning region** — which country their lessons + simulator are geared toward (US / UK / HK key exchanges), defaulting to their home market.
2. **Practice currency** — the display/practice currency (their home currency or another: USD / GBP / HKD), independent of region.

Neither touches the child's legal/consent `country_code`.

**Content reality (verified):** all 12 seeded modules are tagged `country_codes: []` (global), so region does **not** change which lessons show today — that plumbing is future-ready (kicks in when modules are tagged per-country). Region's *visible* effect now is **featuring the chosen exchange in the simulator**; currency is its own independent control.

## Key constraint discovered (load-bearing)

`country_code` currently does **double duty**: (a) content filtering (`module.country_codes` matching in `content.py` + `recommendation_service.py` + `analytics_service.py`) **and** (b) the **COPPA/UK-GDPR consent regime** (`compliance.py` / `consent_service.py` derive the parental-consent age from it). Therefore the region switch must **not** mutate `country_code`. We introduce a separate, decoupled field.

`PATCH /users/me` already accepts `country_code`/`currency_code`/`topic_path` (`PreferencesUpdate`); `Me`/`UserProfile` already return `country_code`/`currency_code`. The simulator Market already lists all three exchanges regardless of country.

## Data model

- New `User.content_region: str | None` (`String(2)`, nullable, default NULL). The child's chosen learning region. **NULL ⇒ fall back to `country_code`.** Hand-written chained Alembic migration (check `alembic heads` from `backend/` first).
- Effective region: a small helper `content_region_for(user) -> str` returning `user.content_region or user.country_code` (in `app/services/content_service.py` or a `User` property). Used everywhere content is region-gated.
- **`country_code` is never written by this feature** — consent/compliance keep using it unchanged.
- Supported regions (validated set): **`US`, `GB`, `HK`**. The exchanges map region→exchange for the simulator focus (US→NASDAQ/NYSE, GB→LSE, HK→HKEX). Currency is a **separate** setting (existing `currency_code`), not derived from region.

## Backend

- **Region-gating swap:** in `content.py` (the two `country_ok` checks), `recommendation_service.py` (lines ~60 + ~404), and `analytics_service.py` — replace `current_user.country_code` / `user.country_code` (where used for `module.country_codes` matching) with `content_region_for(user)`. **Do not** change `compliance.py` / `consent_service.py` (they keep `country_code`).
- **`PATCH /users/me`** (`users.py` + `PreferencesUpdate` in `schemas/user.py`): accept optional `content_region`; validate it ∈ `{US, GB, HK}` (mirror the existing ISO-2 validator style; reject others with 422). `currency_code` is already accepted — the `CurrencySelector` uses it directly and independently.
- **Responses:** add `content_region: str | None` to `UserProfile` (`schemas/user.py`) and the `Me` schema (`schemas/auth.py`) so the UI knows the current region (currency is already returned).
- **Region→exchange map** (US→NASDAQ, GB→LSE, HK→HKEX) — a small frontend constant used by the simulator Market to feature the selected region's exchange first. The currency option list (home + USD/GBP/HKD) is a frontend constant.

## Frontend — two independent controls

Both are accessible, labelled, child-changeable, and live in the child **`ProfileMenu`** (a "Preferences" section); the **region** control also appears as a compact switcher on the **Quests/Learn** + **Market** headers. Both call the existing `PATCH /users/me` client (`updatePreferences`). They are **independent** — changing one never changes the other.

- **`RegionSwitcher`** `{ content_region }` — segmented control **🇺🇸 US · 🇬🇧 UK · 🇭🇰 HK** (current highlighted, `aria-current`; flags `aria-hidden`, real text labels). On change → `updatePreferences({ content_region })` → invalidate `['modules']`, `['recommendations']`, `['module-levels']`/`['level-lessons']`, `['me']` (lessons re-filter when region-tagged modules exist) **and** `['portfolio']`/market queries so the simulator re-features the chosen exchange. Reads current from `me` (`content_region ?? country_code`).
- **`CurrencySelector`** `{ currency_code }` — pick the practice/display currency: the child's **home currency** plus **USD / GBP / HKD** (deduped). On change → `updatePreferences({ currency_code })` → invalidate `['portfolio']`/`['portfolio-history']` (holdings persist; totals re-display converted via the existing `formatCurrency`). Reads current from `me.currency_code`. **No dependency on region.**

## Scope of effect

- **Region (`content_region`):** (a) lesson **modules** + **recommendations** filter by the effective region — *future-ready*, no visible change today since all modules are global; (b) the **simulator Market features the region's exchange first** (e.g. HK → HKEX section/tab on top), still showing the others for global exploration. No change to consent/auth/legal country.
- **Currency (`currency_code`):** the display/practice currency across the simulator + any `formatCurrency` usage. Fully independent of region.
- Out: authoring region-specific lesson content (a separate content/admin task); changing which exchanges *exist* (all three stay available).

## Accessibility & safety

- COPPA: legal `country_code` untouched → no consent-regime change; region/currency are low-risk so the child may change them.
- WCAG 2.2 AA: both controls are real labelled controls with visible focus + current-state indication; `vitest-axe` on new UI. iOS ≥16px; no `maximum-scale`.

## Testing

- **Backend:** `content_region_for` fallback (NULL→country_code, set→used); content/recommendation filtering uses the effective region (a US child with `content_region='HK'` sees HK-tagged modules, and — with all-global seed data — still sees all global modules); `PATCH /users/me` accepts `content_region ∈ {US,GB,HK}` + rejects others (422); `currency_code` PATCH still works; **neither alters `country_code`**; `compliance`/consent still keyed on `country_code`; migration applies (check head). Async tests use the `client`/`db_session` fixtures + `loop_scope="session"`.
- **Frontend:** `RegionSwitcher` (3 options, current highlight, axe) → change calls `updatePreferences({content_region})` + invalidates modules/market queries; `CurrencySelector` (home + USD/GBP/HKD, deduped) → change calls `updatePreferences({currency_code})` + invalidates portfolio; the two are independent; the simulator Market features the chosen region's exchange first.
- `tsc -b`, lint, test, build; backend `ruff` + `pytest`. All CI jobs green.

## Plan shape
Backend-first: T1 `content_region` field + migration + `content_region_for` helper → T2 wire region-gating (content/recommendation/analytics) to the effective region + tests → T3 `PATCH`/schemas/responses (`content_region` + validation; expose `content_region` on Me/UserProfile) + tests → T4 FE `RegionSwitcher` + `CurrencySelector` + API/currency-list (+ tests) → T5 mount both in `ProfileMenu`'s "Preferences" + region switcher on Quests/Market headers + query invalidation → T6 simulator Market features the selected region's exchange first + test → T7 regression + push. Each green-CI.

## Decisions captured
**Two independent settings**: `content_region` (new field; legal `country_code` untouched) + `currency_code` (existing, now child-editable). Regions US/GB/HK; currency = home + USD/GBP/HKD. Region affects lesson filtering (future-ready — modules are all global today) **and** features the region's exchange in the simulator; currency is independent (defaults home, selectable). Child-changeable. Controls in `ProfileMenu` (Preferences) + region switcher on Quests/Market headers. Region-specific lesson *content authoring* is a separate later task.
