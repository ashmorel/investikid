# Market Foundation — Design Spec (Sub-project C1)

**Date:** 2026-06-18
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project C, part 1 of 2)

---

## Programme context

Predecessors live in prod: **0** Gemini lineup, **A** i18n foundation (per-user `users.language`), **B** AI replies in the user's language. Sub-project **C** introduces **Market** as a first-class concept and makes progress per-market. C is split:

- **C1 (this spec) — Market foundation:** the `Market` entity, content↔market association, migration of existing content to a **UK market**, a per-user **home market**, and market-based content filtering. **Behaviorally invisible** — every current user is on the UK market and sees exactly today's content.
- **C2 — Multi-market experience (later spec):** per-market progress (XP, lesson completions, Revise weak-concepts keyed by market) + global engagement (one level/streak/coin-wallet/daily-goal), multi-market enrollment (home + additional, switch active market), aggregate progress, and the frontend.

**Locked programme decisions (carried into the data model):**
- **Progress split:** learning is **per-market** (XP, lesson completions, Revise weak-concepts); engagement is **global** (single level from total XP, daily streak, coin wallet, daily goal). *(Implemented in C2; C1 must not preclude it.)*
- **Content ↔ market:** **one market per module** (a `market_code` FK). Universal/shared lessons are handled in Sub-project E (authored per-market or cloned), not via a shared market.
- **Market = the money axis; language is a separate, global user preference** (shipped in A/B).
- **Curriculum translations are STORED, never translated on-the-fly.** Curated market×language pairs get expert-reviewed translation rows; non-curated pairs are Gemini-translated **on first request and persisted**, then served from storage (same pattern as the existing `GeneratedContent` quiz cache). C1 anticipates this with the market model; the translations table + pipeline are **Sub-project E's** build. C1/C2 must not preclude it.

## Goal

Introduce a first-class `Market`, associate all content with a market, migrate existing content into a **GB (UK) market**, give every user a `home_market_code` (set to `GB`), and filter content by market — with **zero behavior change** (everyone is on GB and sees today's content).

## Non-goals (YAGNI / deferred)

- **Per-market progress + multi-market enrollment** → C2.
- **Deriving a user's market from their country** → C2 (only meaningful once non-GB markets have content).
- **Curriculum translation storage + pipeline** → E.
- **Frontend changes** → none in C1 (content is served identically; no market picker yet).
- **Currency changes** → none; `users.currency_code` is untouched.
- **Removing `modules.country_codes`** → left as a vestigial column (the filter stops using it); a later cleanup removes it.

---

## Architecture

### Unit 1 — `Market` model + registry + seed

New `markets` table, keyed by **ISO-3166 alpha-2 code** (aligns with the existing `users.country_code` / `modules.country_codes`, both `String(2)`):

| Column | Type | Notes |
|---|---|---|
| `code` | `String(2)` PK | `GB, US, AU, CA, IE, ES, FR, DE, HK, SG` |
| `name` | `String(80)` | Display name ("United Kingdom", …) |
| `currency_code` | `String(3)` | GBP, USD, AUD, CAD, EUR, EUR, EUR, EUR, HKD, SGD |
| `default_language` | `String(10)` | Primary authoring language: GB/US/AU/CA/IE/HK/SG→`en`, ES→`es`, FR→`fr`, DE→`de` |
| `has_content` | `Boolean` | `True` only for `GB` at C1; others are seeded-but-empty |
| `is_active` | `Boolean` | `True`; reserved for staging markets later |

Seed all 10 rows in a dedicated seed module (`app/seed/markets.py`, run from the seed runner) AND in the migration (so prod/migrated DBs have them without a separate seed run — see Unit 5). `default_language` values use the same BCP-47 codes as `app/core/languages.py`.

**Interface:** SQLAlchemy `Market` model with `code` as PK; a relationship from `Module` (Unit 2).

### Unit 2 — `Module` → `Market`

- Add `market_code: Mapped[str]` to `Module` — `String(2)`, `ForeignKey("markets.code")`, not-null, `server_default="GB"`, indexed.
- A `Module.market` relationship is optional (not required for filtering by code); add only if it reads cleanly.
- Lessons and Levels inherit their market through `module` (no column added to them).

### Unit 3 — `User` home market

- Add `home_market_code: Mapped[str]` to `User` — `String(2)`, `ForeignKey("markets.code")`, not-null, `server_default="GB"`.
- Returned in the `/users/me` profile (read-only in C1; C2 adds switching).

### Unit 4 — Market-based content filtering

In `app/routers/content.py`, the module list/detail currently gates on `not module.country_codes or content_region_for(current_user) in module.country_codes`. Replace the **region gate** with a **market gate**: `module.market_code == current_user.home_market_code`. Keep the premium gate and age gate exactly as they are. Apply the same market filter to the `app/services/analytics_service.py` module query that currently uses `Module.country_codes`.

- `content_region_for` / `country_codes` are no longer consulted for gating in these paths (left defined; removal is a later cleanup).
- Net effect: a GB user sees all GB modules (= today's content); a module on any other market is hidden.

### Unit 5 — Migration (hand-written, chained)

One Alembic revision (check `alembic heads` first; chain to the current head):
1. `create_table("markets", …)`.
2. **Seed the 10 market rows** via `op.bulk_insert` (so migrated DBs have them; the `app/seed/markets.py` module is for fresh local/test seeds and must be idempotent/upsert to match).
3. `add_column("modules", market_code String(2) NOT NULL server_default 'GB')` + FK to `markets.code` + index; existing rows backfill to `GB`.
4. `add_column("users", home_market_code String(2) NOT NULL server_default 'GB')` + FK; existing rows backfill to `GB`.
5. `downgrade`: drop the two columns, then `drop_table("markets")`.

Additive + backfilled; no data loss. FK order: create `markets` before adding the FKs.

---

## Data flow

```
Request → content router has current_user (home_market_code, default 'GB')
        → list modules WHERE module.market_code == current_user.home_market_code
          AND (age gate) AND (premium gate)
        → identical module set to today for every (GB) user
```

## Error handling / edge cases

- **Existing users / modules:** backfilled to `GB` by the migration → no nulls, no empty curricula.
- **New registrations (C1):** `home_market_code` defaults to `GB` (column default). Deriving from country is C2.
- **A user somehow on a market with no content:** not reachable in C1 (everyone is `GB`); C2's enrollment guards against selecting empty markets.
- **FK integrity:** `markets` is created+seeded before the FK columns are added.

## Testing strategy

- **Model/seed:** `markets` has all 10 codes with correct currency/default_language; `GB.has_content is True`, others `False`. Seed module is idempotent.
- **Migration:** applies on a populated DB; existing modules → `GB`, existing users → `GB`; downgrade reverses cleanly.
- **Filtering regression (the key test):** a GB user's `/content` module list equals the pre-C1 set (seed all current modules → GB). A module created on a `US` market is **not** returned to a GB user; it **is** returned to a `home_market_code='US'` user. Premium/age gating still applies on top.
- **Profile:** `/users/me` includes `home_market_code == "GB"`.
- **Full backend suite + `ruff` green;** CI's full run is authoritative.

## Definition of done

1. `Market` entity exists with all 10 markets seeded; only `GB` has `has_content=True`.
2. Every existing module is on the `GB` market; every existing user has `home_market_code='GB'`.
3. Content is served **byte-identically** to today for current (GB) users (regression test green); non-GB-market modules are correctly hidden.
4. The migration is additive + backfilled with a clean downgrade.
5. All backend tests + ruff green; promoted testing → staging → main.

## Rollout / safety

- The migration touches `modules` and `users` (adds columns + a new table) in prod. **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- Behaviorally inert for the current all-GB user base.
- Promote testing → staging → main on green CI per the standard flow.
