# Content Localization Pipeline — Design Spec (Sub-project E1)

**Date:** 2026-06-19
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project E, part 1 of 2)

---

## Programme context

Predecessors live in prod: **0** Gemini lineup, **A** i18n (UI catalogs + `users.language`), **B** AI-language (LLM replies in the user's language), **C1/C2a/C2b** market layer + frontend, **D** cross-market rewards. Authored curriculum is hand-written English in `backend/app/seed/content.py` (~2,686 lines), served straight from the DB with **no language layer** (`ModuleOut(title=m.title)`, `LessonOut(content_json=...)`). The 5 non-English supported languages (es/fr/de/zh-Hant/zh-Hans) are flagged `available: False`; no translation scaffolding exists.

**E is split** into **E1 (this spec) — the content-localization pipeline (language axis)** and **E2 — per-market content waves (market axis, the follow-up)**. E1 is the reusable engine: once it exists, whatever content exists (GB today; other markets as E2 lands) is automatically multilingual.

**Locked decisions (from the E1 brainstorm):**
- **Storage = one row per `(entity_type, entity_id, language)`** holding a JSON bundle mirroring that entity's translatable fields, plus `source`/`source_hash`/`status`.
- **Generation = admin-triggered batch; labelled `auto` translations go live immediately** (no human gate); idempotent + staleness via `source_hash`; curated translations override auto.
- **Gate = structural validation + `moderate_output`**; failures are not served and fall back to English (unlabelled).
- **Serving = per-entity fallback**; each entity served in the user's language if a translation exists (labelled machine-translated when `auto`), else English.
- **Scope = all learner-facing text except video transcripts** (transcripts stay English; the videos are English-audio).

## Goal

Serve InvestiKid's authored content in a user's chosen language from **stored** translations — expert-curated where available, Gemini auto-translated (validated, moderated, labelled) otherwise — with per-entity English fallback and **zero on-the-fly translation at serve time**. Behaviorally inert until an operator generates a batch and flips a content language on.

## Non-goals (deferred)

- **Per-market new curriculum** — that's E2. E1 localizes whatever content exists (GB today).
- **Video transcript translation** — out of scope (long, low value for English-audio videos); transcripts stay English as the a11y fallback.
- **Localized audio/video.**
- **Automatic re-translation cron** — staleness is *detected* (source_hash) and falls back to English; re-translation happens on the next admin batch.
- **UI chrome translation** — that's the sub-project A i18n catalogs, separate.

---

## Architecture

### Unit 1 — `ContentTranslation` model

New table; one row per `(entity_type, entity_id, language)`.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `entity_type` | String(10) | `'module' \| 'level' \| 'lesson'` |
| `entity_id` | UUID | the module/level/lesson id |
| `language` | String(10) | BCP-47 (`es`/`fr`/`de`/`zh-Hant`/`zh-Hans`) |
| `translated_json` | JSONB | bundle mirroring the entity's translatable fields |
| `source` | String(10) | `'curated' \| 'auto'` (curated wins) |
| `source_hash` | String(64) | hash of the English source bundle this was made from |
| `status` | String(10) | `'active' \| 'failed'` (failed = rejected by the gate; not served) |
| `created_at` / `updated_at` | timestamptz | |

Composite **unique** `(entity_type, entity_id, language)`. Index on `(entity_type, language)` for batch/coverage queries. No FK to the content tables (polymorphic `entity_id`); orphan rows are harmless and cleaned by re-seed tooling if needed.

### Unit 2 — Translatable-field extraction (single source of truth)

A pure module (e.g. `app/services/content_i18n.py`) defining **what is translatable**, used by the extractor, validator, and serving layer so they never drift:
- `extract(entity_type, entity) -> dict` — the English bundle: module `{title, conversation_prompt}` (omit `None`); level `{title, learning_objectives: [...]}`; lesson `content_json` text by `type` — card `{title, body}`, quiz/scenario `{question, options: [...], explanation, ...}` (the real text keys present), video `{caption}`. **Excludes** video `transcript`, `youtube_id`, answer indices, ids, xp, and any non-text field.
- `source_hash(bundle) -> str` — stable hash (e.g. sha256 of canonical JSON) of the English bundle; drives staleness.
- `apply(entity_type, served_fields, bundle) -> served_fields` — overlay a translation bundle onto the entity's served fields (title/content_json/etc.) for serving; only overrides keys present in the bundle, leaving excluded fields (transcript, youtube_id, indices) intact.

### Unit 3 — Translation service

`translate_entity(session, entity_type, entity, language) -> ContentTranslation | None`:
1. `bundle = extract(entity_type, entity)`; `h = source_hash(bundle)`.
2. **Idempotency/staleness:** existing row for `(entity_type, entity_id, language)`?
   - `source == 'curated'` → never overwrite (return as-is).
   - `status == 'active'` and `source_hash == h` → fresh, return as-is.
   - else (missing / stale / previously failed) → regenerate.
3. Call the LLM (**Gemini standard tier** from the lineup) with the English bundle + a structured instruction: return the *same JSON shape* translated into the target language; keep proper nouns, company/ticker names, numbers, and any answer-index fields unchanged.
4. **Gate:**
   - **Structural validation** — parsed JSON has the same keys, same number of `options` (if any), unchanged answer-index field(s), all strings non-empty.
   - **Safety** — `moderate_output(serialized_text, surface="content", language=language)` (sub-project B).
   - Pass → upsert `source='auto', status='active', source_hash=h, translated_json=<parsed>`.
   - Fail → upsert `status='failed'` (recorded, not served → the entity falls back to English unlabelled, and it shows in coverage). A subsequent `generate` run re-attempts `failed`/stale rows (they aren't `active`-with-matching-hash), so failures are retryable but not retried within the same batch.

### Unit 4 — Batch generation + curated override (admin)

- `POST /admin/translations/generate { language, market_code? }` — iterate content entities (optionally scoped to a market by `module.market_code`), call `translate_entity` for each missing/stale one, return `{translated, skipped_fresh, failed}`. Rate-limited (LLM-backed); re-runnable (idempotent via `source_hash`).
- `PUT /admin/translations/curated { entity_type, entity_id, language, translated_json }` — store/replace a `curated` translation (same **structural** validation; curated is human-authored so it **bypasses moderation**). Curated always overrides `auto` at serve time.
- `GET /admin/translations/coverage?language=` — per-language coverage: `active` / `failed` / `missing` counts by entity type, so an operator knows when a language is ready to offer.

### Unit 5 — Language-aware serving

Helper `localize(entity_type, entity, served_fields, language, translations) -> (fields, machine_translated: bool)`:
- `language == 'en'`, unknown, **or not in the enabled content languages** (Unit 7) → return English fields, `machine_translated = False` (fast no-op, byte-identical to today). The content-availability gate is checked once per request, not per entity.
- else → look up the `active` `ContentTranslation`; if present, `apply()` its bundle and set `machine_translated = (source == 'auto')`; else English fields, `machine_translated = False`.

Wire into every content-serving site keyed on `current_user.language`: `list_modules`, `_get_accessible_module`, level/lesson lists, `lesson detail`, `next-lesson`, and the Revise feeders. Batch-load the relevant `ContentTranslation` rows per request (avoid N+1). Because serving is gated on the enabled-content-languages set, generated-but-not-yet-enabled translations sit dormant until an operator flips the language on.

### Unit 6 — Label surfacing

Add `machine_translated: bool = False` to `ModuleOut`, `LessonOut`, and the level/lesson summaries. The frontend renders a small, i18n'd "Machine-translated" chip on content carrying the flag. Curated translations serve with no chip (flag `False`).

### Unit 7 — Content-language availability

UI-catalog `available` (sub-project A) and **content** availability are different axes. Add a DB-backed, admin-flippable **content availability** setting in `app_settings` — `content_languages.enabled` (JSON list of language codes; default empty) — with a typed getter (`get_enabled_content_languages`) and an admin settings field to edit it. **This set gates serving** (Unit 5): the `localize` path returns English unless the user's language is in it, so generated translations stay dormant until an operator enables the language (the kill-switch that makes E1 inert on deploy). The `LanguageSwitcher` still *offers* a language based on its **UI catalog** availability; content availability is the independent operator control over whether stored translations are actually served. No code deploy to launch (or pull) a content language.

### Unit 8 — Migration (hand-written, chained)

One additive Alembic revision (check `alembic heads`; chain to the current head): `create_table("content_translations", …)` with the unique constraint + index. No change to existing content tables; no backfill (translations are generated by the admin batch post-deploy). `downgrade` drops the table.

---

## Data flow

```
Admin: POST /admin/translations/generate { language: "fr" }
  → for each module/level/lesson:
       bundle = extract(entity); h = source_hash(bundle)
       fresh/curated? skip : LLM(bundle → fr) → structural + moderate gate
         pass → store ContentTranslation(auto, active, h)
         fail → store status=failed (English fallback)
  → {translated, skipped_fresh, failed}

Admin: PUT /admin/translations/curated {...}  → curated row (overrides auto)
Admin: flip content_languages.enabled += "fr"

Child (language=fr) requests content
  → serving loads ContentTranslation rows for the entities
  → localize(entity, "fr"): active translation? apply bundle + machine_translated flag : English
  → ModuleOut/LessonOut carry localized text + machine_translated
  → UI shows a "Machine-translated" chip where flagged
```

## Error handling / edge cases

- **Stale source (English edited):** `source_hash` mismatch → that entity falls back to English until the next batch re-translates it. No broken/stale text served.
- **Gate failure (bad structure / moderation):** stored `failed`; entity serves English, unlabelled. Visible in coverage.
- **Curated present:** never overwritten by generation; serves without the machine-translated chip.
- **English / unknown language:** no-op English path; no DB lookup cost beyond the (empty) batch load.
- **LLM/provider error mid-batch:** that entity is counted `failed` (or skipped) and the batch continues; re-running the batch retries it (idempotent).
- **Partial coverage:** per-entity fallback means a half-translated market is coherent per entity; never blocks a language.
- **N+1:** translations are batch-loaded per request for the entities being served.

## Testing strategy

- **Extraction:** `extract`/`source_hash`/`apply` round-trip per entity type; transcripts/ids/indices excluded; `apply` leaves excluded fields intact.
- **Translation service:** idempotency (fresh `source_hash` → skip), staleness (changed source → regenerate), curated never overwritten; the gate rejects a dropped quiz option / moved answer index (structural) and unsafe output (moderation → `failed`).
- **Serving:** per-entity fallback (translated entity localized + flagged; missing entity English); `machine_translated` true for auto, false for curated/English; English user path byte-identical (regression).
- **Admin endpoints:** generate returns correct counts + is idempotent on re-run; curated override stores + supersedes; coverage reports active/failed/missing.
- **Availability:** the content-language setting round-trips via admin; serving/offer respects it.
- **Migration:** additive create/drop clean.
- **Full backend suite + ruff; frontend tsc + lint + test + build (incl. the badge + `vitest-axe`); i18n guard; CI authoritative.**

## Definition of done

1. `ContentTranslation` stores per-entity translation bundles with `source`/`source_hash`/`status`; one additive migration.
2. The translation service generates Gemini auto-translations of the English source, passing a structural + moderation gate; curated overrides; idempotent + staleness-aware.
3. Admin can generate a language batch, import curated translations, and read coverage.
4. Content serves in the user's language per-entity with English fallback and a machine-translated label on `auto`; English behavior is byte-identical (regression green).
5. A content language is admin-flippable on/off without a deploy.
6. Scope = all learner-facing text except video transcripts.
7. All backend + frontend + CI jobs green; promoted testing → staging → main; Vercel prod for the badge.

## Rollout / safety

- Additive migration (`content_translations`). **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- **Behaviorally inert** until an operator runs a generation batch and flips a content language on — English users and all current behavior are unchanged.
- Gemini calls are **operator-triggered batches** (cost controlled; never per request).
- Promote testing → staging → main on green CI; then the manual Vercel prod web deploy for the badge.
