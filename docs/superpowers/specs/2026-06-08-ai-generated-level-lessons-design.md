# AI-Generated Level Lessons + Admin Review (Leveled Progression 15.2) — Design Spec

**Date:** 2026-06-08
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Builds on:** 15.1 Levels foundation (`Level` between Module and Lesson), the existing LLM stack (`get_llm_client` tiers), the fail-closed moderation seam (`moderate_output`), the admin Level/Lesson CRUD, and the proven `generate_practice_quiz` pipeline (LLM → validate → moderate → store).

## Goal

Let an admin **AI-generate a batch of draft lessons** for a level, **review/edit** them, and **approve** the safe ones into live `Lesson`s. Moderation is enforced on every draft; unreviewed or unsafe content can never reach a child.

## Decisions (from brainstorming)

1. **Separate `lesson_drafts` table** — drafts live entirely outside the `Lesson` serving path, so a child can never see an unreviewed/unsafe draft. Approve materialises a real `Lesson`.
2. **Batch generation** — one "generate" produces `count` draft lessons for a level, round-robining the selected text types.
3. **Flag-don't-discard on moderation failure** — a draft that fails `moderate_output` stays in the queue marked flagged (category shown) but is **un-approvable**.
4. **Text types only** — `card`, `quiz`, `scenario`. **`video` is excluded** (AI cannot supply a safe curated YouTube id).
5. **Premium LLM tier** for generation (`get_llm_client("premium")`); admin-only; rate-limited.

## Section 1 — Data

**New model `app/models/lesson_draft.py` → table `lesson_drafts`:**
- `id` UUID PK.
- `level_id` Mapped[UUID] FK → `levels.id` (index).
- `type` String — one of `card|quiz|scenario`.
- `content_json` JSON/JSONB.
- `concept` String — the topic the admin requested.
- `model_used` String — the LLM model name (`get_model_name`).
- `moderation_safe` Boolean, nullable=False.
- `moderation_category` String | None.
- `created_at` timezone-aware (mirror existing models).

Register in `app/models/__init__.py`. **Hand-written chained Alembic migration** (run `alembic heads` first — current head `a5b6c7d8e9f0`; `down_revision` = the single head at implementation time). `create_table` up / `drop_table` down.

## Section 2 — Generation service

**New `app/services/admin_content_generation_service.py`** (mirrors `ai_content_service.generate_practice_quiz`):

- A reusable validator: extract the per-type `content_json` checks from `app/schemas/admin.py`'s `validate_content` into a pure helper `validate_lesson_content_json(type, content_json) -> None` (raises `ValueError`), and have the existing schema call it (DRY — one source of truth for both admin-authored and AI-generated lessons).
- Per-type **prompt builders** producing strict JSON instructions for the exact `content_json` shape:
  - `card` → `{title, body}`
  - `quiz` → `{question, choices[2–5], answer_index, explanation}`
  - `scenario` → `{prompt, choices[{label, outcome}] (≥2), correct_index}`
- `async def generate_level_lessons(session, level, *, concept, count, types) -> GenerationResult`:
  1. Load the parent `Module` for `level` (topic, `min_age`/`max_age`, title) to ground the prompt (age band + topic).
  2. For each slot `i` in `range(count)`, pick `lesson_type = types[i % len(types)]`.
  3. `client = get_llm_client("premium")`; `raw = await client.complete(system_prompt, messages=[...], response_format="json", temperature=~0.4, max_tokens=~700)`.
  4. `json.loads(raw)` → `validate_lesson_content_json(lesson_type, parsed)`. On `JSONDecodeError`/`ValueError`: retry **once**; if still bad, **skip** this slot and record it in `GenerationResult.skipped`.
  5. `mod = await moderate_output(_concat_text(parsed), surface="lesson")`. Persist a `LessonDraft(level_id, type, content_json=parsed, concept, model_used=get_model_name(...), moderation_safe=mod.safe, moderation_category=mod.category)`. If `not mod.safe`, also log a content-free `AuditLog(event_type="moderation_block", ...)` (same as the quiz pipeline).
  6. `await session.commit()`; return `GenerationResult(created=[draft...], skipped=n)`.
- `_concat_text(parsed)` joins the human-readable string fields per type (title/body/question/choices/explanation/prompt/labels/outcomes) for moderation.
- Wrap LLM calls so an `LLMError`/provider outage surfaces as a clean error to the endpoint (no partial-uncommitted state); already-created drafts in the batch are committed.

## Section 3 — Admin endpoints

All under `get_current_admin`; mutations use the normal session + CSRF (like other admin routes). Schemas in `app/schemas/admin.py` (or a new `app/schemas/lesson_draft.py`): `GenerateLessonsRequest{concept: str, count: int (1–8), types: list[Literal["card","quiz","scenario"]] (non-empty)}`, `LessonDraftOut{id, level_id, type, content_json, concept, moderation_safe, moderation_category, created_at}`, `LessonDraftUpdate{content_json: dict}`.

- `POST /admin/levels/{level_id}/generate` — body `GenerateLessonsRequest` → `generate_level_lessons` → returns `{created: LessonDraftOut[], skipped: int}`. **Rate-limited** `@limiter.limit("5/minute")` (and the slowapi `Request` param). 404 if the level doesn't exist.
- `GET /admin/levels/{level_id}/drafts` → `LessonDraftOut[]` (pending drafts for the level, ordered by `created_at`).
- `PUT /admin/lesson-drafts/{draft_id}` — body `LessonDraftUpdate` → re-run `validate_lesson_content_json` (422 on invalid) + **re-moderate** (`moderation_safe`/`category` recomputed) → returns the updated `LessonDraftOut`.
- `POST /admin/lesson-drafts/{draft_id}/approve` → if `moderation_safe` is False → **409** `"Draft failed moderation"`; else create `Lesson(module_id=level.module_id, level_id, type, content_json, xp_reward=<default, e.g. 10>, order_index=<max+1 in that level>)`, delete the draft, commit, return the new `LessonOut`.
- `POST /admin/lesson-drafts/{draft_id}/regenerate` → re-generate one lesson of the **same `type` + `concept`** (single-slot call into the service), replace the draft's `content_json`/`moderation_*`/`model_used` in place, commit, return `LessonDraftOut`. Rate-limited.
- `DELETE /admin/lesson-drafts/{draft_id}` → reject (delete), 204.

## Section 4 — Admin UI

Frontend `src/api/admin.ts` hooks: `useGenerateLevelLessons(levelId)`, `useLevelDrafts(levelId)`, `useUpdateDraft()`, `useApproveDraft()`, `useRegenerateDraft()`, `useRejectDraft()` — all via the existing `adminFetch`/`apiFetch` (session + CSRF), invalidating `['level-drafts', levelId]` (and `['level-lessons', levelId]` on approve).

- **Generate affordance** on the level's lesson-management screen (near `LevelLessonList`): a **"✨ Generate lessons"** button opening a small form — `concept` (text), `count` (1–8), and type checkboxes (card/quiz/scenario) → calls generate → shows a spinner while the (slow) LLM batch runs → reveals the drafts. Surfaces `skipped` count if any slot failed.
- **`LessonDraftReview`** component (new): a list of draft cards, each with: a **type badge**, a **rendered preview** of the content (reuse/inline the per-type rendering the child lesson renderers already use where practical, else a simple structured preview), a **moderation badge** — `Safe ✓` (success token) or `⚠ Flagged: {category}` (danger token) — and actions: **Edit** (inline editor reusing the existing `LessonForm` per-type editors), **Approve** (disabled + tooltip when flagged), **Regenerate**, **Reject** (ConfirmDialog). Accessible (labelled controls, ≥44px targets, keyboard, axe-clean), Penny/sky semantic tokens. Admin desktop surface.

## Section 5 — Safety, gating, limits

- **Moderation is mandatory** on generation and on every edit; flagged drafts are un-approvable in **both** the UI (disabled) and the backend (409). Fail-closed (a moderation error → treat as unsafe).
- **Admin-only** (`get_current_admin`) + **rate-limited** generate/regenerate (`5/minute`) so a mass-generate can't hammer the LLM providers.
- Approved lessons inherit premium from their `is_premium` level — no separate child gate.
- **No child-facing surface changes**; the `Lesson` serving path and `derive_level_states` are untouched. Drafts are invisible to children by construction.

## Section 6 — Testing

**Backend pytest** (`loop_scope="session"`, `db_session`/`client`; patch `get_llm_client`/`moderate_output` the way the existing `tests/test_ai_content*`/quiz tests do — read them for the mock pattern):
- `validate_lesson_content_json`: accepts valid card/quiz/scenario, rejects each missing-field / bad-index case (and the existing admin schema still rejects the same — no regression).
- `generate_level_lessons`: with a mocked LLM returning valid JSON + `moderate_output` safe → creates `count` drafts of the right round-robined types, all `moderation_safe=True`; with a mocked unsafe `moderate_output` → draft persisted with `moderation_safe=False` + category + an `AuditLog`; with the mock returning invalid JSON once then valid → retried; with persistently bad JSON → that slot skipped (`skipped` incremented), others created.
- Endpoints: admin-auth required (anon → 401/403); `generate` happy path returns created/skipped; `approve` on a flagged draft → 409 and no Lesson created; `approve` on a safe draft → materialises a `Lesson` (correct `module_id`/`level_id`/`order_index`) and deletes the draft; `PUT` edit re-validates (422 on invalid) + re-moderates; `reject` deletes; rate-limit decorator present.
- Migration: `alembic heads` single after adding it.

**Frontend vitest + vitest-axe:**
- Generate form submits `{concept, count, types}` and renders returned drafts.
- `LessonDraftReview`: a flagged draft shows the danger badge and a **disabled** Approve; a safe draft's Approve calls `useApproveDraft`; Edit opens the editor and Save calls `useUpdateDraft`; Reject (confirm) calls `useRejectDraft`; Regenerate calls `useRegenerateDraft`. No axe violations.

**Verify:** backend `ruff check .` + `pytest`; frontend `npx tsc -b` + `npm run lint` + `npm run test` + `npm run build`. Admin is a web/desktop surface — no `cap sync` needed.

## Out of scope
Generating `video` lessons; generating whole *levels* (the admin still creates the Level shell, then generates its lessons); auto-publishing without admin approval; child-facing changes; the 15.1 follow-up of adding transcript/captions fields to the admin video editor (separate); 15.3 level-aware recommendations/analytics (separate sub-project).
