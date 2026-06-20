# Per-Market Curriculum Engine — Design Spec

**Date:** 2026-06-20
**Status:** Draft for review
**Owner:** Lee Ashmore

## Goal

Give each market its own **independent, market-native curriculum** — distinct modules, levels, concepts, examples, and questions designed from that market's verified facts — instead of UK lessons with the currency swapped. Make the UK (GB) curriculum regenerable to the same bar, and fix the draft-review flow so the operator never leaves the Market Content tab.

## Background / problem

Three operator-reported problems with the current E2/E2.1 market-content pipeline:

1. **Clunky review flow.** "Review N drafts" navigates to the generic admin Levels page (`LevelLessonList`), whose back-link returns to the admin module-levels list — not Market Content — and approving leaves the operator stranded there.
2. **UK can't be regenerated.** GB is the hand-authored source every other market adapts from, so there is deliberately no way to regenerate GB.
3. **Markets feel identical.** The "Generate lessons (from GB)" / "Generate all" buttons run the *adapt-from-GB* path, whose system prompt instructs the model to *"Keep the learning objective, structure… identical"* and only *"Replace UK products, regulators, currency…"*. By construction it produces currency-swapped clones.

Root cause of #2/#3 is the same: market content is derived from GB line-by-line. The fix is to generate each market natively from its brief, and to treat GB as just another market.

A **market-native generator already exists** (`generate_native_level_lessons` → `POST /admin/levels/{id}/generate-native`): it ignores GB text and writes fresh lessons grounded only in the market's verified `MarketBrief`. It is almost certainly what produced the better US modules the operator noticed. This project builds the curriculum-design layer on top of it and retires the adapt path for market content.

## Decisions (confirmed in brainstorming)

- **Content approach:** fully independent per-market curricula (own modules/levels/concepts), not a stronger adapt prompt.
- **Coverage:** a must-cover **concept backbone** every market must satisfy, with free expression (own modules, ordering, depth, local topics, all examples) beyond it.
- **Progressive complexity:** as levels advance, the curriculum must cover the backbone concepts in increasing complexity and detail — a spiral curriculum. The designer assigns each level a complexity tier; the generator writes to that tier.
- **UK (GB):** regenerated through the same flow but as **drafts only**. Live UK lessons stay untouched until the operator reviews and approves a replace.
- **Rollout:** build the engine, prove it **end-to-end on US first**, then roll out to the other 8 markets + GB.
- **Review UX:** draft review happens **inline inside the Market Content tab** (recommended option); approve/publish returns the operator to the market list.

## The concept backbone

A canonical list, defined in code, that every market must cover. Each market is free to add more topics, choose ordering and depth, and write all examples itself.

1. **Earning & income** — where money comes from, the value of work
2. **Spending & budgeting** — needs vs wants, making a plan
3. **Saving & goals** — setting money aside, short- and long-term goals
4. **Banking & accounts** — keeping money safe, how accounts work
5. **Borrowing & debt** — credit, interest you pay, borrowing wisely
6. **Growing money & compound interest** — investing basics, money over time
7. **Risk & diversification** — why values change, not all eggs in one basket
8. **Financial safety & scams** — protecting money, spotting fraud
9. **Tax & giving** — how tax works locally and the role of charitable giving

Each entry: `{ key, title, description }`. Lives in `backend/app/services/market_curriculum/backbone.py` as a static list (operator-editable later if needed — out of scope now, YAGNI).

### Progressive complexity model

Three complexity tiers, assigned by the designer to every proposed level:

- **1 — Foundational:** first exposure; concrete, simple, single idea.
- **2 — Developing:** builds on the basics; introduces mechanics and trade-offs.
- **3 — Advanced:** applies and combines ideas; nuance, edge cases, real decisions.

Requirements the designer must satisfy and the validator enforces:

- Every backbone concept is covered by ≥1 level.
- The curriculum spans all three tiers (not all foundational).
- When a backbone concept recurs across levels, its complexity is **non-decreasing** in curriculum order (it deepens, never regresses).
- Tier broadly tracks module/level order and the market's age band (earlier ≈ foundational, later ≈ advanced).

The tier is passed into native generation so each lesson is written at the right depth.

## Architecture

Five units, each independently testable. New code lives under `backend/app/services/market_curriculum/`.

### 1. Backbone (`backbone.py`)
Static `BACKBONE: list[ConceptDef]` + helper `backbone_keys()`. No I/O. Pure data.

### 2. Curriculum designer (`designer.py`)
`design_curriculum(session, *, market_code, brief) -> CurriculumProposal`

- Premium LLM call. System prompt: design a complete finance-education curriculum for `market_code`, grounded **only** in the verified brief (local products, regulators, currency, culture, local examples) and these age bands; cover every backbone concept; assign a complexity tier per level; scaffold tiers so concepts deepen as levels advance; this is NOT a UK curriculum — no UK-specific products/regulators/currency.
- Output JSON shape (validated; uses `extract_json_list` discipline for any array-at-top-level risk):
  ```json
  { "modules": [
      { "topic": "...", "title": "...", "icon": "💷", "min_age": 10, "max_age": 14,
        "order_index": 0,
        "levels": [
          { "title": "...", "order_index": 0, "complexity_tier": 1,
            "learning_objective": "...",
            "concepts": ["short concept the lesson teaches", "..."],
            "backbone_keys": ["saving", "budgeting"] }
        ] } ] }
  ```
- Returns a `CurriculumProposal` domain object (not yet persisted).

### 3. Coverage + progression validator (`validator.py`)
`validate(proposal) -> ValidationReport` — pure function over the proposal:
- `missing_backbone: list[str]` (keys with no covering level)
- `tiers_present: set[int]` and `spans_all_tiers: bool`
- `regressions: list[...]` (a backbone concept whose tier decreases in order)
- `ok: bool`
The designer service runs the validator and **retries once** with the gaps fed back if `not ok`; the persisted proposal still carries the final report so the operator sees any residual gaps.

### 4. Proposal persistence + materialisation (`proposal_service.py`)
New table **`market_curriculum_proposal`** (one migration, chained off current head — check `alembic heads` first):
- `id` (uuid pk), `market_code` (str, indexed), `status` (`proposed|accepted|superseded`), `proposal_json` (JSON — the tree, with a `level_id` slot per node filled on accept), `coverage_json` (JSON — the ValidationReport), `created_at`, `accepted_at` (nullable).
- One **active** (`proposed`/`accepted`) proposal per market at a time; re-running the designer marks the prior `superseded`.

`accept_proposal(session, proposal)`:
- Creates `Module` + `Level` rows from the tree, `has_content=false`, drafts pending, using existing fields (topic/title/icon/min_age/max_age/order_index/market_code on Module; title/order_index/pass_threshold on Level).
- Writes each created `level_id` back into the proposal node and sets `status='accepted'`.
- The accepted proposal is the source of truth for each level's `concepts` + `complexity_tier` at generation time (no new columns on `Level`).

### 5. Native generation batch (`market_native_batch.py`)
`generate_market_native(session, module, *, brief, include_populated)` — mirrors the existing per-module batch runner but calls `generate_native_level_lessons` with the level's `concepts` + `complexity_tier` read from the accepted proposal, instead of the from-GB adapt path. Reuses the proven safeguards from the current batch: per-level rollback isolation, skip levels that already have published lessons **or pending drafts** (unless `include_populated`), and `skipped_*` accounting.

Small extension to native generation: `generate_native_level_lessons` (and `_system_prompt`'s native branch) gain an optional `complexity_tier` that adds a depth instruction to the prompt ("write at a foundational/developing/advanced level: …"), so the same concept is written shallower or deeper according to where it sits in the spiral. Tier is optional and defaults to the current behaviour when absent.

### Retiring the adapt path (market content)
- Native generation replaces from-GB adapt for market content. The from-GB `generate_market_level_lessons` and its endpoints/buttons are removed from the Market Content flow (the function may remain if still referenced by older code paths, but is no longer wired to the market UI).
- The existing US currency-swapped drafts are discarded as part of the US pilot.

## Data flow

```
verified MarketBrief + backbone
   → designer.design_curriculum  (LLM, validate+retry)
   → proposal persisted (status=proposed, coverage report)
   → operator reviews in Market Content (coverage shown; accept / regenerate)
   → accept_proposal → Module/Level rows (has_content=false)
   → generate_market_native (per module / whole market) → LessonDrafts
   → operator reviews drafts inline in Market Content → approve / publish(&replace)
   → lessons live; has_content flips true when a module is fully covered
```

## API endpoints (admin, rate-limited, `require_verified_brief` where market-scoped)

- `POST /admin/markets/{market_code}/curriculum/design` → runs designer, persists proposal, returns proposal + coverage. (Rate-limited; premium LLM.)
- `GET  /admin/markets/{market_code}/curriculum` → current active proposal + coverage (or 404).
- `POST /admin/markets/{market_code}/curriculum/accept` → materialise modules/levels; returns created ids.
- `POST /admin/modules/{module_id}/generate-native-batch` → native batch for a module (uses accepted proposal). Whole-market run loops modules client-side, as today.
- Existing draft approve / publish-replace endpoints are reused unchanged.

## Frontend (Market Content tab)

- **Curriculum panel** per market: if no accepted curriculum, show "Design curriculum" (calls `/design`), then render the proposed module/level tree with **backbone-coverage chips** (✓ per covered concept, ⚠ for gaps) and complexity-tier badges; actions: **Accept** / **Regenerate**.
- After accept, the existing module/level list renders with native **Generate** (per-module + whole-market) buttons wired to `generate-native-batch`.
- **Inline draft review (#1 fix):** the level row expands in place (or opens a panel scoped to that level) showing its drafts with Approve / Publish-&-replace; on success it stays in Market Content and refreshes counts. The standalone `LevelLessonList` review path is no longer the entry point for market drafts.
- i18n keys added under `marketContent.curriculum.*` and `marketContent.review.*`.

## Error handling

- Designer LLM returns malformed/again-malformed JSON → surface "Couldn't design a curriculum, try again"; nothing persisted.
- Validator gaps after retry → proposal still saved; operator sees the ⚠ chips and can Regenerate.
- Accept is atomic (one commit); partial failure rolls back, no orphan modules.
- Native batch keeps per-level rollback isolation; one level failing never leaks drafts into the next (existing behaviour).
- Unverified brief → 409 (existing guard).

## Testing

- `backbone`: all 9 keys present, unique.
- `validator`: detects missing backbone key; detects tier regression; passes a well-formed spiral; flags all-foundational.
- `designer`: with a mocked LLM, returns a valid proposal; retries once on a gap and surfaces residual gaps.
- `proposal_service`: accept materialises correct module/level counts with `has_content=false`; re-design supersedes prior; writes level_ids back.
- `market_native_batch`: generates from the accepted proposal's concepts+tier (not GB); skips populated **and** pending-draft levels; rollback isolation.
- Endpoints: design→accept→generate happy path; unverified-brief 409; unknown market 404.
- Frontend: curriculum panel renders coverage chips + tier badges; Accept enables generation; inline review approves without leaving Market Content; vitest-axe on new UI.

## Rollout / pilot

1. Build the engine behind the Market Content tab.
2. **US pilot end-to-end:** design → review coverage → accept → native-generate → review drafts → publish. Operator judges quality.
3. On sign-off, roll to AU/CA/IE/ES/FR/DE/HK/SG.
4. **GB last**, drafts-only: regenerate, review, approve a replace of the live authored lessons only on explicit sign-off.

## Out of scope (YAGNI)

- Operator-editable backbone (static list for now).
- In-UI editing/reordering of the proposed tree (Accept / Regenerate only; edit individual modules via existing admin tools after accept).
- Translating generated curricula across languages (E1 pipeline already exists; runs after publish).
- Any change to the child-facing learning experience beyond the new content itself.

## Open questions

None outstanding — backbone (9 incl. Tax & giving), progressive complexity, UK drafts-only, US pilot, and inline review are all confirmed.
