# Market Content — Lesson Markers, Replace-on-Regenerate & Batch Generation — Design Spec

**Date:** 2026-06-20
**Status:** Approved (design); ready for implementation plan
**Programme:** E2/E2.1 market-content operator tooling (follow-on)

---

## Context

Operating the admin **Market Content** page (`/admin/market-content`) for the US market surfaced two gaps in the per-level lesson-generation step:

1. **No "already done" indicator.** After generating lessons for a level, approving the drafts, and returning to Market Content, nothing shows that the level already has published lessons — so an operator can unknowingly generate + approve again.
2. **Approve appends, it does not overwrite.** `POST /admin/lesson-drafts/{id}/approve` creates a **new** `Lesson` (`order_index = max+1`) and deletes the draft. So regenerating a level that already has lessons and re-approving **duplicates** them. The operator expected "overwrite"; today it stacks.
3. **One level at a time.** Generation is per-level (`POST /admin/levels/{id}/generate-market`), tedious for a whole market. Constraints: the LLM endpoints are rate-limited **5/minute**, and a single long request risks a proxy timeout (an earlier ~65-sequential-call scaffold timed out).

Established facts the design relies on:
- The admin Level API already returns `lesson_count` per level (frontend `AdminLevel.lesson_count`, `useLevels`), and `AdminModule.lesson_count` per module — so the marker needs no backend change.
- Approving a draft = create `Lesson` + delete `LessonDraft` (`approve_lesson_draft`); unsafe drafts (`moderation_safe=false`) are blocked from approval.
- The frontend currently resolves each market level's GB **source** level itself (match market module→GB module by `topic`+`order_index`, then market level→GB level by `order_index`) and passes `source_level_id` to `generate-market`.
- The draft-review screen is a separate route (`/admin/modules/{moduleId}/levels/{levelId}/lessons` → `LessonDraftReview`), distinct from the Market Content tab.

(FYI: "Suggest modules" returning `[]` is **not** a bug — the prod log shows `200` with no error; the model proposed nothing for US. The earlier object-wrapping parse bug is already fixed.)

**Locked decisions (from the brainstorm):**
- **Replace on regenerate** (not warn-only): a destructive replace, but committed only at an explicit, atomic point after review.
- **Batch = per-module server-side endpoint + a market-wide sequential frontend runner.**
- **Batch skips levels that already have lessons by default**, with an override toggle.

## Goal

Make the operator's market-content workflow safe and fast: show which levels are already done, let a regenerate cleanly **replace** old lessons (atomically, post-review), and generate a whole module/market in batches without hitting the rate limit or timing out.

## Non-goals (deferred)

- Auto-publishing or auto-approving drafts — review stays mandatory.
- An async/queued job system (market-wide runs sequentially from the client).
- Changing the GB-source matching heuristic (topic+order_index) — reused as-is.
- Suggester prompt tuning (separate, optional later).
- Editing the per-draft review/edit/regenerate/reject flow (unchanged).

---

## Architecture

### Unit A — Published-lesson marker (frontend only)

In `MarketContent.tsx`'s `LevelGenerator` row, render a badge from the level's existing `lesson_count`:
- `lesson_count > 0` → **"✓ {{n}} published"** (success styling).
- `lesson_count === 0` → muted "No lessons yet."

`useLevels(moduleId)` already supplies `lesson_count`; the data is invalidated after generate/approve via the existing query keys. No backend or schema change. Module-level rollup ("✓ N levels done") may be shown from `AdminModule.lesson_count`/per-level counts if cheap, but the per-level badge is the requirement.

### Unit B — Replace-on-regenerate (backend + draft-review frontend)

**Backend — atomic level approve-with-replace.** New `POST /admin/levels/{level_id}/approve-drafts` (admin-gated), body `{ replace: bool = false }`:
1. Load the level (404 if missing).
2. If `replace`: delete all existing `Lesson` rows under `level_id`.
3. Approve every **moderation-safe** draft for the level — create a `Lesson` per draft (contiguous `order_index`), delete the draft. Unsafe drafts are left untouched (not approved, not deleted), mirroring the per-draft gate.
4. One transaction (all-or-nothing): old lessons are deleted **only** when the replacements are created, so a failure leaves the prior published set intact. Returns `{ approved: int, replaced: int, skipped_unsafe: int }`.

This is the **explicit commit point** — nothing destructive happens at generate or review time, only here.

**Frontend.**
- *Market Content* (`LevelGenerator`): when `lesson_count > 0`, the generate control reads **"Regenerate (replace)"** and, on click, shows a confirm — *"This level has N published lessons. The new lessons you approve will replace them."* — then runs the existing `generate-market` (creates fresh drafts, old lessons untouched) and surfaces the review link as today.
- *Draft review* (`LessonDraftReview`): add a level-level **"Publish & replace existing (N)"** button (shown when the level has drafts and ≥1 published lesson) → confirm → `approve-drafts {replace:true}`. Also add a plain **"Approve all"** (`replace:false`) for the additive case. Per-draft approve/edit/regenerate/reject stay unchanged. On success, invalidate the level-drafts + level-lessons + levels/modules queries so the marker updates.

### Unit C — Batch generation (backend + frontend)

**Backend — per-module batch.** New `POST /admin/modules/{module_id}/generate-market` (admin-gated, `@limiter.limit("5/minute")`, `require_verified_brief(module.market_code)`), body `{ include_populated: bool = false }`:
1. Resolve the GB **source module**: `Module` where `market_code="GB"` and matching `topic` + `order_index` (the heuristic the frontend uses). If none → 409/422 with a clear message.
2. For each level in the target module (ordered): resolve the GB source level by `order_index` within the source module. Skip a target level when: no unique GB source matched, OR (`not include_populated` AND the level already has lessons). Otherwise call the existing `generate_market_level_lessons(target_level, source_level, brief)` (which already skips non-generatable `video` lessons).
3. **Best-effort per level**: a level's generation error is caught, logged, counted — it never aborts the module. Returns a per-level summary `{ levels: [{level_id, status: generated|skipped_populated|skipped_no_source|error, created, skipped}], totals }`.
4. One HTTP request per module (~3 levels) keeps it well under the proxy timeout; being a single endpoint call, it consumes one unit of the 5/min budget regardless of how many internal LLM calls it makes.

**Frontend.**
- A per-module **"Generate all levels"** button (calls the module batch; default skip-populated) with a result summary.
- A market-wide **"Generate all"** that iterates the market's modules and calls the per-module batch **sequentially**, showing a progress indicator (`module i of N`, per-module created/skipped). It spaces requests to respect the 5/min limit and backs off on a `429`; it continues past a failed module and reports which failed. An "include levels that already have lessons" checkbox sets `include_populated`.

---

## Data flow

```
Marker:  useLevels(module) → level.lesson_count → "✓ N published" badge

Replace: Market Content "Regenerate (replace)" → confirm → generate-market (new drafts; old lessons intact)
         → review screen → "Publish & replace existing (N)" → POST /levels/{id}/approve-drafts {replace:true}
         → (txn) delete old lessons + approve safe drafts → marker updates

Batch:   "Generate all levels" → POST /modules/{id}/generate-market {include_populated:false}
            → resolve GB source module → per level: match GB level, skip populated, generate (best-effort)
         "Generate all (market)" → for each module: await the per-module batch (sequential, rate-limit-aware, progress)
```

## Error handling / edge cases

- **No verified brief:** module batch 409 (same gate as per-level generate).
- **No GB source module/level match:** that level is `skipped_no_source` (batch) or the per-level control stays disabled (today's behavior); never a crash.
- **Replace with zero safe drafts:** if `replace` and there are no approvable drafts, do **not** delete existing lessons (avoid emptying a level on an empty draft set) — return `approved:0, replaced:0` and surface a "nothing to publish" message. (Guard explicitly.)
- **Rate limit (429) on the market runner:** the client backs off and retries that module rather than failing the run.
- **Batch timeout safety:** scope is per-module only; the whole market is never one request.
- **Best-effort batch:** one level/module failure is reported, others proceed.

## Testing strategy

- **Unit A:** `LevelGenerator` shows the published badge when `lesson_count>0` and the empty state otherwise (frontend test).
- **Unit B (backend):** `approve-drafts {replace:true}` deletes existing lessons and approves safe drafts atomically; unsafe drafts skipped; `{replace:false}` appends; **empty-safe-draft replace does NOT delete** existing lessons; counts correct.
- **Unit B (frontend):** the "Publish & replace existing" button calls the endpoint with `replace:true` behind a confirm; "Approve all" uses `replace:false`; marker/queries invalidate.
- **Unit C (backend):** module batch resolves the GB source module, generates for empty levels, **skips populated** by default and includes them when `include_populated`, is best-effort per level (one error doesn't abort), 409 without a verified brief.
- **Unit C (frontend):** per-module button calls the batch; the market runner sequences modules, shows progress, continues past a failed module, and respects the toggle.
- **Full gates:** backend ruff + pytest; frontend tsc + lint + test + build; CI authoritative.

## Definition of done

1. Each level in Market Content shows whether it already has published lessons.
2. Regenerating a populated level can **replace** its lessons — committed atomically only when the operator clicks "Publish & replace" after reviewing the new drafts; nothing is deleted before that, and an empty draft set never empties a level.
3. An operator can generate a whole module in one click and a whole market via a sequential, progress-tracked, rate-limit-aware runner that skips already-done levels by default.
4. Drafts still require human review; no auto-publish. No DB migration. CI green; promoted testing → staging → main; manual Vercel prod for the admin UI.

## Rollout / safety

- **No migration** (marker reads existing counts; replace/batch reuse existing tables + the generation service). No prod snapshot question.
- Admin-only, rate-limited, premium-model (operator-triggered). Child-facing behavior unchanged. Promote testing → staging → main on green CI; manual Vercel prod for the admin bundle.

---

## Self-review

- **Placeholders:** none — endpoints, request bodies, the atomic replace transaction, the GB-source resolution, and the skip rules are all specified.
- **Consistency:** the marker (A) reflects what replace (B) and batch (C) change (`lesson_count` via the existing invalidations). Replace is the single destructive op and is atomic + guarded against emptying on no-drafts. Batch reuses `generate_market_level_lessons` (already video-safe) and the per-level GB-source heuristic.
- **Scope:** operator tooling for the existing generate→review→publish pipeline; no auto-publish, no async jobs, no migration, suggester tuning deferred.
- **Ambiguity:** the replace commit point ("Publish & replace" on the review screen, not at generate/approve-per-draft time) and the no-empty-on-empty-drafts guard are stated explicitly.
