# Per-Market Content Waves — Design Spec (Sub-project E2)

**Date:** 2026-06-19
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (Sub-project E, part 2 of 2)

---

## Programme context

The multi-market layer is live: markets, per-market progress, the C2b picker, D rewards, E1 content-localization (translates authored content across *languages*), and the multi-market premium gate (free users get one market). Today only **GB has content** — 15 hand-authored modules (`backend/app/seed/content.py`), `market_code` defaulting to GB; the other 9 markets are `has_content=false`.

**E2 (this spec)** delivers real curriculum to the empty markets so each flips `has_content=true` and becomes completable. It is **market adaptation** (different money-specifics), distinct from E1's **language translation** — and the two compose (adapt GB→US for the market, then E1 translates US→es/fr/zh for language).

**The platform already has the generation + review machinery** (discovered during design): `admin_content_generation_service.py` generates `LessonDraft` rows via the **premium model** with schema-validation + moderation; admin endpoints generate (`POST /admin/levels/{id}/generate`), list (`GET /admin/levels/{id}/drafts`), edit (`PUT /admin/lesson-drafts/{id}`), and **approve into real `Lesson`s** (`POST /admin/lesson-drafts/{id}/approve`); plus full module/level/lesson CRUD. E2 **extends** this to be market-aware — it does not build a CMS or a generator from scratch.

**Locked decisions (from the E2 brainstorm):**
- **Production = a market-adaptation generator** grounded in GB as a pedagogical scaffold; auto-publish is forbidden — **expert review before go-live** is mandatory (kids' finance, regulatory accuracy).
- **Lifecycle = real `Module`/`Lesson` rows tagged `market_code=<target>`, kept invisible by `has_content=false`, reviewed/edited in place, then published by flipping `has_content`.** Content is already gated by `market_code` + `has_content`, so no draft store is needed.
- **Grounding = a `MarketBrief`** (currency, accounts, regulators, products, examples) — **LLM-drafted, human-verified** — fed to the generator so output is genuinely market-specific, not reskinned GB.
- **Scope = the pipeline + a US pilot.** E2 ships the mechanism and proves it end-to-end on US (English, closest to GB). The other 8 markets are operator-driven runs of the same pipeline. US go-live waits on human review (operator), not the code build.

## Goal

Ship a market-adaptation content pipeline — verified per-market brief → GB-scaffolded structure → market-grounded lesson generation (premium model, moderated) → human review/approve → per-market publish — that makes any empty market completable, and prove it end-to-end producing US drafts. The pipeline ships **inert** (no market published until an operator runs it and reviews).

## Non-goals (deferred)

- **Authoring all 9 markets in this build** — the remaining 8 are operator content waves on the shipped engine.
- **A content-diff / translation-memory** between GB and markets.
- **Per-market simulator/region content** (separate axis).
- **Auto-publish** — review is mandatory.
- **Language translation of a market's content** — E1 already does that.

---

## Architecture

### Unit 1 — `MarketBrief` model + migration

New per-market record (the grounding keystone):

| Column | Notes |
|---|---|
| `market_code` | PK, FK `markets.code` |
| `brief_json` | JSONB — structured facts: `{ currency, tax_advantaged_accounts[], regulators[], deposit_protection, typical_products[], local_examples[], notes }` |
| `status` | `'draft' \| 'verified'` (generation gated on `verified`) |
| `model_used` | the model that drafted it |
| `created_at` / `updated_at` | |

One additive Alembic migration (chain to head `d3f6a9c0b1e2`); `create_table("market_briefs", …)`; downgrade drops it. No change to existing tables.

### Unit 2 — Brief generation + verification

In a small `market_brief_service.py`:
- `generate_brief(session, market_code) -> MarketBrief` — premium model drafts the structured facts for that market (grounded in the model's knowledge of the market's financial system), schema-validated, stored `status='draft'`.
- Admin endpoints: `POST /admin/markets/{code}/brief/generate` (draft), `GET /admin/markets/{code}/brief` (read), `PUT /admin/markets/{code}/brief` (edit `brief_json`), `POST /admin/markets/{code}/brief/verify` (set `status='verified'`).
- A helper `require_verified_brief(session, market_code)` used as the gate by scaffold + generation.

### Unit 3 — Market-grounded generation (the adaptation core)

Extend the existing generator (`admin_content_generation_service.py`) to be market-aware — the single change that makes output market-specific:
- `_system_prompt(...)` gains optional `brief` + `source_lesson` (the GB reference). When present, it instructs: *adapt this GB lesson's concept into <market> using these verified facts — replace UK products/regulators/examples (ISA→Roth IRA, FCA→SEC, £→$) with the market's real equivalents from the brief; keep the learning objective, structure, and age level; do not copy GB specifics.*
- A new `generate_market_level_lessons(session, target_level, *, source_level, brief)` — for each lesson under the GB `source_level`, generate one adapted `LessonDraft` under `target_level`, grounded in `brief` + that GB lesson. Reuses the existing `_generate_one` plumbing (premium model, schema validation, moderation, `LessonDraft` storage). Blocked unless the brief is `verified`.
- Admin endpoint: `POST /admin/levels/{level_id}/generate-market` (body: `source_level_id`) → drafts for the target level.

### Unit 4 — Scaffold a market from GB

`POST /admin/markets/{code}/scaffold` (service `scaffold_market_from_gb`): clone GB's **module + level skeleton** into the target market — new `Module`/`Level` rows, `market_code=code`, `has_content` untouched (false): copy `topic`, `order_index`, `icon`, `is_premium`, prerequisite structure, `pass_threshold`; **module/level `title` + `learning_objectives` are market-adapted** by a small premium-model call grounded in the verified brief (not copied — "ISAs explained" → "Roth IRAs explained"). Lessons are not generated here (that's Unit 3, per level). Idempotent (skips a market that already has scaffolded modules). Requires a verified brief.

### Unit 5 — Publish / unpublish a market

`POST /admin/markets/{code}/publish` flips `has_content=true`; `POST /admin/markets/{code}/unpublish` flips it back. Publish is **guarded**: rejected unless the market has ≥1 module with ≥1 approved `Lesson` (no empty go-live). Reversible. Once published, the premium gate, per-market progress, D rewards, and E1 translation all operate on the market with no special-casing.

### Unit 6 — Admin frontend

Extend the admin content area with a per-market workflow: generate/edit/verify the brief; scaffold from GB; per-level generate-market + the existing draft review/approve UI; publish/unpublish the market. Reuse the existing draft-review components; all strings i18n'd (`admin` namespace).

### Unit 7 — US pilot (validation, operator-reviewed)

E2's build proves the pipeline by generating US **drafts** end-to-end in a non-prod env (brief → scaffold → adapted lessons) and confirming they're market-specific (dollars, Roth IRA/401(k), SEC/FDIC — not GB relabels). **Publishing US (`has_content` flip) waits on human expert review** (operator), so the code build delivers the proven pipeline + US drafts; go-live is the operator's call. The other 8 markets follow as operator waves.

---

## Data flow

```
Admin: POST /admin/markets/US/brief/generate → MarketBrief(draft)
Admin: edit + POST .../brief/verify → MarketBrief(verified)
Admin: POST /admin/markets/US/scaffold
   → clone GB modules/levels → US (market_code=US, has_content=false),
     titles/objectives adapted via brief
Admin: per US level → POST /admin/levels/{us_level}/generate-market { source_level_id: gb_level }
   → for each GB lesson: premium-model adapt (brief + GB ref) → LessonDraft (moderated)
Admin: review drafts (PUT /admin/lesson-drafts/{id}) → approve (POST .../approve) → real Lessons
Admin: POST /admin/markets/US/publish → has_content=true (guarded: ≥1 approved lesson)
Child (active=US): content now served; premium gate + progress + E1 all apply
```

## Error handling / edge cases

- **Generation without a verified brief:** 409/422 — blocked; the brief gate is enforced in scaffold + generate.
- **Publish with no lessons:** rejected (guard); a market can't go live empty.
- **Re-scaffold:** idempotent — skips already-scaffolded modules (no duplicates).
- **Moderation/schema failure on a draft:** the existing pipeline marks it unsafe / skips (reused as-is); the admin sees it in review.
- **GB unchanged:** scaffold/generate only create `market_code=<target>` rows; GB rows are read-only references. Regression-guarded.
- **Unpublish:** hides the market again (sets `has_content=false`); existing per-market progress rows are retained (not deleted).

## Testing strategy

- **`MarketBrief`** model + lifecycle (draft → verified); generation/scaffold blocked until verified.
- **Brief generation** returns structured facts (mock the LLM); edit + verify round-trip.
- **Scaffold** clones GB's module/level skeleton into the target market (count + structure match, `market_code` set, `has_content` still false, titles adapted via a mocked LLM, idempotent re-run).
- **Market generation** (`generate_market_level_lessons`): the prompt includes the brief + GB reference (assert via a mock-LLM spy); drafts pass schema + moderation; blocked without a verified brief.
- **Publish** flips `has_content` only with ≥1 approved lesson; empty rejected; unpublish reverses.
- **Regression:** GB content/serving byte-identical; the premium gate + per-market progress + E1 operate on a published market with no special-casing; existing draft-generation tests stay green.
- **Pilot:** US brief → scaffold → drafts generated end-to-end (mocked LLM in CI; a real run in a non-prod env for human spot-check).
- **Full backend + frontend + ruff; CI authoritative.**

## Definition of done

1. `MarketBrief` exists; LLM-drafted, human-verified; generation gated on `verified`.
2. The generator is market-aware (brief + GB reference → adapted draft) reusing the premium-model + moderation pipeline.
3. Scaffold clones GB's skeleton into a target market with adapted titles/objectives; idempotent.
4. Per-market publish/unpublish flips `has_content`, guarded against empty go-live.
5. Admin UI runs the whole workflow (brief → scaffold → generate → review/approve → publish).
6. The US pipeline runs end-to-end producing market-specific drafts (not GB relabels); GB unchanged; premium gate + progress + E1 work on a published market.
7. Additive migration; all backend + frontend + CI jobs green; promoted testing → staging → main; Vercel prod for the admin UI. Pipeline ships **inert** (no market published without operator review).

## Rollout / safety

- Additive migration (`market_briefs`). **Per the standing rule, ask whether to snapshot the prod DB before applying in production.**
- **Ships inert:** no market is published until an operator generates + verifies the brief, generates + **reviews** the content, and flips `has_content`. No unreviewed AI curriculum reaches a child — drafts are premium-model + moderated + **human-reviewed** before go-live.
- Generation is admin-only, rate-limited (reuses the existing limiter), premium-model (operator-triggered batches — cost controlled).
- Promote testing → staging → main on green CI; then the manual Vercel prod web deploy for the admin UI. US (and later markets) go live as operator content waves after review.
