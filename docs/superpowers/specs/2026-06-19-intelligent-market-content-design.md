# Intelligent Market Content — Design Spec (Sub-project E2.1)

**Date:** 2026-06-19
**Status:** Approved (design); ready for implementation plan
**Programme:** Multi-language + multi-market localization (E2 follow-on)

---

## Context

E2 shipped the market-adaptation pipeline (verified `MarketBrief` → scaffold from GB → market-grounded generation → review/approve → publish). Operating it surfaced two needs:
1. **A copy-paste safety net** — ensure generated drafts are genuinely adapted, not GB reskins.
2. **Proactive curriculum shaping** — the model should *propose* modules each market genuinely needs (e.g. US college savings / 529s, credit scores) and let the operator create them in one click, rather than the market being locked to the cloned UK module set.

This sub-project makes the admin **Market Content** page intelligent + proactive while keeping the human in control (suggestions are advisory; creation is one-click but operator-initiated; nothing publishes without review).

**Locked decisions (from the brainstorm):**
- **Adaptation guard = deterministic UK-residue token scan**, no extra LLM call, no DB change; surfaced as a review badge. (GB-source text-similarity is deferred — it would require storing each draft's source on the row, i.e. a migration; residue is the high-signal copy-paste check and needs no source linkage.)
- **Module suggestions are model-generated**, grounded in the verified brief + the current GB module list, returning add/replace recommendations with rationale.
- **One-click "Create this module"** scaffolds the module (+ a starter level) so the page is proactive.
- **Created (non-GB-derived) modules generate lessons market-NATIVE** (grounded in the brief, no GB source).

## Goal

Make per-market content demonstrably market-appropriate, not UK copy-paste: auto-flag un-adapted drafts in review, and let the model propose + one-click-create market-specific modules that then generate brief-grounded native lessons — all human-reviewed before publish.

## Non-goals (deferred)

- Auto-publishing anything (review stays mandatory).
- Auto-deleting/replacing GB-derived modules (a "replace" suggestion creates the new module + flags the old one; the operator deletes via existing CRUD).
- Cross-market suggestion sharing / templates.
- Changing the existing GB→market adaptation path (unchanged).

---

## Architecture

### Unit 1 — Adaptation guard (deterministic)

New `app/services/content_adaptation_check.py`:
- `UK_RESIDUE_TERMS` — UK-specific tokens: `£`, `ISA`, `FCA`, `HMRC`, `National Insurance`, `Premium Bonds`, `NS&I`, `pence`, `pound`/`pounds`, `GBP`, `Junior ISA`, `Help to Save`, `NHS`, etc. (word-boundary matched, case-insensitive; `£` matched directly).
- `find_uk_residue(text) -> list[str]` — returns the UK terms present. Pure, fast, no LLM.
- Surface on the draft-list endpoint (`GET /admin/levels/{id}/drafts`): for each `LessonDraft`, run `find_uk_residue` over its concatenated text and add to `LessonDraftOut` as `adaptation_flags: {uk_residue: [...], suspect: bool}` (`suspect = uk_residue non-empty`). No DB column — computed at read time, so it applies to existing drafts too.
- Frontend: the draft review row shows a **"⚠ May not be fully adapted"** badge listing the residue terms when `suspect`.

### Unit 2 — Module suggester

New `app/services/market_module_suggester.py`:
- `suggest_modules(session, market) -> list[ModuleSuggestion]` — one **premium** call (now fast at minimal reasoning), grounded in the **verified brief** + the **current GB module titles/topics**. Prompt: *propose modules this market needs that the UK set lacks, and flag UK-specific modules to replace; for each give a title, topic, one-line rationale, action (`add`|`replace`), the replaced GB module title (if `replace`), and 3–5 suggested lesson concepts.* Structural-validated; on failure returns `[]` (graceful).
- `ModuleSuggestion = {title, topic, rationale, action, replaces, suggested_concepts: [str]}`.
- Endpoint `POST /admin/markets/{code}/module-suggestions` (admin-gated, rate-limited, `require_verified_brief`).

### Unit 3 — One-click "Create this module"

Endpoint `POST /admin/markets/{code}/modules/from-suggestion` (admin-gated), body = a `ModuleSuggestion`:
- Creates a `Module` (`market_code=code`, the suggested `title`/`topic`, `order_index = max(existing market order)+1`, sensible defaults: `is_premium=False`, an icon, `prerequisite_ids=[]`) **+ one starter `Level`** (title e.g. "Level 1", `order_index=0`) so lessons can be generated into it. No lessons; `has_content` untouched.
- Returns the created module + level ids (so the UI can jump to native generation).
- The suggested concepts are returned/stored so the native generator can use them.

### Unit 4 — Market-native lesson generation

Created modules have no GB source, so extend the generator for a **brief-only (native)** mode:
- `_system_prompt(..., brief=…, source_text=None)` — when `brief` is present but `source_text` is None, instruct: *write a market-native {type} lesson for market X on this concept, grounded in these verified facts; use the market's real products/regulators/currency; age-appropriate.* (The existing GB-adaptation mode — both brief + source_text — is unchanged; the generic mode — neither — is unchanged.)
- `generate_native_level_lessons(session, level, *, brief, concepts, types)` — for each concept, `_generate_one(..., brief=brief.brief_json, source_text=None)` → `LessonDraft`. Reuses validate + moderation + storage.
- Endpoint `POST /admin/levels/{level_id}/generate-native` (body: `{concepts: [str], types?: [str]}`), `require_verified_brief(target_module.market_code)`.

### Unit 5 — Frontend (the proactive page)

In `MarketContent.tsx`:
- A **"Suggest modules"** action (enabled once the brief is verified) → renders the suggestions list: each card shows title, topic, rationale, an `Add`/`Replace` chip (and the GB module it replaces), and a **"Create this module"** button → calls `from-suggestion`, then surfaces the created module's level with a **"Generate lessons"** (native) control wired to `generate-native` using the suggested concepts → feeds the existing draft review (now with the Unit 1 adaptation badges).
- All strings i18n'd (`admin` namespace). Reuse existing admin styling.

---

## Data flow

```
Admin (brief verified) → POST /admin/markets/US/module-suggestions
   → premium model (brief + GB module list) → [{title, topic, rationale, action, replaces, concepts}]
Admin clicks "Create this module" → POST /admin/markets/US/modules/from-suggestion
   → new Module(market_code=US) + starter Level (no lessons)
Admin "Generate lessons" → POST /admin/levels/{level}/generate-native {concepts}
   → brief-grounded NATIVE LessonDrafts (moderated)
Admin reviews drafts → each flagged by the adaptation guard (UK residue / similarity)
   → correct/approve → Publish (existing)
```

## Error handling / edge cases

- **No verified brief:** suggestions + native generation 409 (same gate as scaffold/generate).
- **Suggester LLM failure:** returns `[]` (the UI shows "no suggestions / try again"), never 500s the page.
- **Adaptation guard:** read-time only; a missing GB source (native modules) → similarity skipped, residue still checked. Never blocks; purely advisory.
- **"Replace" suggestion:** creates the new module + flags the GB one in the rationale; the operator removes the old one via existing module-delete (no auto-delete).
- **Duplicate create:** creating the same suggestion twice makes two modules (operator-controlled); no dedupe (YAGNI), but order_index keeps them ordered.

## Testing strategy

- **Adaptation check:** residue terms detected (e.g. "£500 in your ISA" → `["£","ISA"]`); a clean US text → `[]` → `suspect=False`. Draft-list returns the flags per draft.
- **Suggester:** mocked LLM → parsed `ModuleSuggestion`s; 409 without a verified brief; `[]` on malformed output.
- **from-suggestion:** creates a market module + starter level, correct order_index, no lessons, `has_content` untouched; market-scoped.
- **Native generation:** `_system_prompt` native mode includes the brief + concept and NOT a GB source; `generate_native_level_lessons` makes one draft per concept (mock LLM); 409 without a verified brief; the GB-adaptation + generic prompt modes are byte-identical (regression).
- **Frontend:** suggestions render with Create buttons; create → native-generate → drafts; adaptation badge shows on a suspect draft; a11y; i18n guard.
- **Full backend + frontend + ruff; CI authoritative.**

## Definition of done

1. The draft review flags drafts with UK residue or high GB-similarity ("may not be fully adapted").
2. The Market Content page suggests market-specific modules (brief-grounded, add/replace + rationale + concepts).
3. "Create this module" scaffolds the module + a starter level in one click.
4. Created modules generate market-NATIVE lessons grounded in the brief (no GB source); existing GB-adaptation + generic generation unchanged.
5. All human-reviewed before publish; no auto-publish/auto-delete.
6. No migration (computed flags + reused tables). All CI jobs green; promoted testing → staging → main; Vercel prod for the admin UI.

## Rollout / safety

- **No DB migration** (the adaptation flags are computed at read time; modules/levels reuse existing tables). No snapshot question.
- Admin-only, rate-limited, premium-model (operator-triggered). Ships behind the existing admin gate; child-facing behavior unchanged until an operator creates modules + publishes.
- Promote testing → staging → main on green CI; manual Vercel prod for the admin UI.
