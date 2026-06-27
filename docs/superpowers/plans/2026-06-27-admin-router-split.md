# Admin God-Router Split — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Split the 1329-line `backend/app/routers/admin.py` god-router into domain sub-routers, with `admin.py` kept as a thin aggregator — zero API change, behaviour byte-identical.

**Architecture:** `admin.py` keeps its `APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])` but loses all route functions; it `include_router(...)`s domain sub-routers (`admin_content`, `admin_generation`, `admin_drafts`, `admin_markets`, `admin_gamification`, `admin_translations`, `admin_media`, `admin_settings`). Each sub-router is a bare `APIRouter()` (NO prefix, NO dependencies — both are inherited when the aggregator is mounted, so auth runs exactly once) holding that domain's routes + its private helpers + its own imports. Schemas already live in `backend/app/schemas/admin.py` (no move). `main.py`'s `include_router(admin_router.router)` is unchanged. Paths stay relative (`/modules`, `/levels/{id}`…) so every URL is identical.

**Tech Stack:** FastAPI, SQLAlchemy async, pytest (async `admin_client` fixture).

## Global Constraints

- **Zero API change:** every route's final path, method, response model, and the `get_current_admin` auth must be byte-identical after the split. Sub-routers carry NO `prefix`/`dependencies` of their own (the aggregator provides both); adding them would double-run auth.
- **Move, don't rewrite:** copy each route function + its private helpers verbatim from `admin.py` into the target module, moving only the imports each one needs. Do not change logic, signatures, or paths.
- **Test patch-paths must follow the code:** four test files monkeypatch `app.routers.admin.<symbol>`; when the symbol moves, update the patch path to the new module:
  - `tests/test_video_assets_admin.py` → `admin_mod.storage` / `app.routers.admin.storage` → `app.routers.admin_media`
  - `tests/test_admin_translations.py` → `app.routers.admin.translate_entity` → `app.routers.admin_translations`
  - `tests/test_lesson_draft_endpoints.py` → `app.routers.admin.moderate_output` → `app.routers.admin_drafts`
  - `tests/test_llm_probe.py` → `app.routers.admin.probe_all_providers` → `app.routers.admin_settings`
- **Verification per task:** `ruff check backend/` (whole dir incl tests — must be clean), and the admin endpoint tests touching the moved domain (run via the `admin_client` fixture) green. CI is authoritative.
- **Use the shared venv** at `/Users/leeashmore/Local Repo/.venv` for backend commands. Commit straight to `main`; commit body ends `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- After each task, `admin.py` must remain importable and the app must start (every route either still in admin.py OR moved into a sub-router that is `include_router`'d).

## File Structure

- Keep: `backend/app/routers/admin.py` → reduced to aggregator (router decl + `include_router` calls + any residual that genuinely belongs nowhere else; aim for ~0 routes).
- Create: `backend/app/routers/admin_content.py`, `admin_generation.py`, `admin_drafts.py`, `admin_markets.py`, `admin_gamification.py`, `admin_translations.py`, `admin_media.py`, `admin_settings.py`.
- Each sub-router: `from fastapi import APIRouter, Depends, …` + `router = APIRouter()` + the moved routes/helpers + that domain's imports.
- The aggregator wires them: `from app.routers import admin_content, admin_generation, …` then `router.include_router(admin_content.router)` … (one per sub-router).

> **Domain → source line ranges in the CURRENT `admin.py`** (read the file to copy exact bodies; line numbers are a guide, confirm by function name):
> - **content**: `_upsert_apply_mission` (131), `_lesson_out` (155), `_level_out` (398); routes `get_stats`(169), modules CRUD/reorder/restore (184–310), lessons CRUD/reorder (311–394), levels CRUD + level-lessons (408–498).
> - **generation**: `generate_level_lessons_endpoint`(502), `generate_market_level_lessons_endpoint`(523), `generate_module_market_lessons_endpoint`(551), `generate_native_level_lessons_endpoint`(569), `generate_native_batch_endpoint`(1309), market-curriculum design/get/accept/publish (1241–1308).
> - **drafts**: list/update/approve/approve-level/regenerate/reject (594–695); uses `moderate_output`.
> - **markets**: brief generate/get/update/verify (698–753), scaffold(754), module-suggestions(768), module-from-suggestion(782), publish/unpublish (821–849).
> - **gamification**: badges (852–899), challenges (901–939).
> - **translations**: `_fetch_entity`(1060); generate/curated/coverage (1022–1144); uses `translate_entity`.
> - **media**: `_video_health_items`(1146); video-health, video-health/check, video-assets/presign (1171–1213); uses `storage`.
> - **settings**: countries(941), settings get/put (950–1020), users/{id}/premium(1215), llm-status(1230); uses `probe_all_providers`.

---

### Task 1: Extract `admin_content.py`

**Files:** Create `backend/app/routers/admin_content.py`; Modify `backend/app/routers/admin.py`.

**Interfaces:**
- Produces: `admin_content.router` (bare `APIRouter()`), holding the content/curriculum routes + `_upsert_apply_mission`, `_lesson_out`, `_level_out`.

- [ ] **Step 1:** Read `admin.py`. Create `admin_content.py` with `router = APIRouter()` and MOVE (cut from admin.py, paste here) the content/curriculum routes + the three helpers listed under "content" above, plus exactly the imports those bodies use (FastAPI, SQLAlchemy, schemas from `app.schemas.admin`, services, models). Decorators become `@router.<method>("<relative path>")` unchanged.
- [ ] **Step 2:** In `admin.py`, add `from app.routers import admin_content` and `router.include_router(admin_content.router)`. Remove the moved code from admin.py. Remove now-unused imports from admin.py.
- [ ] **Step 3:** `ruff check backend/` → clean (fix unused imports in BOTH files).
- [ ] **Step 4:** Run the content admin tests (e.g. `tests/test_admin_modules.py`, `test_admin_lessons*`, `test_admin_levels*`, any stats test) via `.venv` pytest → green. App imports (`python -c "import app.main"`). **CRITICAL auth check** (this is the first task that relies on the aggregator's `dependencies` propagating to a bare sub-router): confirm a moved endpoint still enforces auth — an UNauthenticated request to a moved path (e.g. `GET /admin/modules` via the plain `client` fixture, not `admin_client`) must return 401/403, not 200. If the existing suite lacks such a case, add one. If it returns 200, the aggregator is not applying `get_current_admin` to merged routes — STOP and fix (e.g. pass `dependencies=[Depends(get_current_admin)]` on the `include_router` call) before proceeding.
- [ ] **Step 5:** Commit `refactor(admin): extract admin_content router`.

---

### Task 2: Extract `admin_generation.py` + `admin_drafts.py`

**Files:** Create `backend/app/routers/admin_generation.py`, `backend/app/routers/admin_drafts.py`; Modify `admin.py`, `backend/tests/test_lesson_draft_endpoints.py`.

- [ ] **Step 1:** Create both modules (`router = APIRouter()` each). Move the generation routes into `admin_generation.py` and the draft routes (+ they use `moderate_output`) into `admin_drafts.py`, with the imports each needs. Add both `include_router` calls to `admin.py`; remove moved code + unused imports.
- [ ] **Step 2:** Update `tests/test_lesson_draft_endpoints.py`: change the patch target `app.routers.admin.moderate_output` → `app.routers.admin_drafts.moderate_output`.
- [ ] **Step 3:** `ruff check backend/` clean.
- [ ] **Step 4:** Run the generation + draft tests (`test_lesson_draft_endpoints.py`, any generate-endpoint tests, `test_market_content*` if they hit generation) → green. App imports.
- [ ] **Step 5:** Commit `refactor(admin): extract admin_generation + admin_drafts`.

---

### Task 3: Extract `admin_markets.py` + `admin_translations.py`

**Files:** Create `admin_markets.py`, `admin_translations.py`; Modify `admin.py`, `backend/tests/test_admin_translations.py`.

- [ ] **Step 1:** Create both (`router = APIRouter()`). Move market routes → `admin_markets.py`; move translation routes + `_fetch_entity` helper (+ they use `translate_entity`) → `admin_translations.py`, with needed imports. Add both `include_router` calls; remove moved code + unused imports from admin.py.
- [ ] **Step 2:** Update `tests/test_admin_translations.py`: `app.routers.admin.translate_entity` → `app.routers.admin_translations.translate_entity`.
- [ ] **Step 3:** `ruff check backend/` clean.
- [ ] **Step 4:** Run market + translation admin tests (`test_admin_translations.py`, `test_market_*` admin-side, brief/scaffold/publish tests) → green. App imports.
- [ ] **Step 5:** Commit `refactor(admin): extract admin_markets + admin_translations`.

---

### Task 4: Extract `admin_gamification.py` + `admin_settings.py`

**Files:** Create `admin_gamification.py`, `admin_settings.py`; Modify `admin.py`, `backend/tests/test_llm_probe.py`.

- [ ] **Step 1:** Create both (`router = APIRouter()`). Move badges + challenges → `admin_gamification.py`; move countries + settings + users/{id}/premium + llm-status → `admin_settings.py` (it uses `probe_all_providers`), with needed imports. Add both `include_router` calls; remove moved code + unused imports.
- [ ] **Step 2:** Update `tests/test_llm_probe.py`: `app.routers.admin.probe_all_providers` → `app.routers.admin_settings.probe_all_providers` (both occurrences).
- [ ] **Step 3:** `ruff check backend/` clean.
- [ ] **Step 4:** Run gamification + settings tests (`test_llm_probe.py`, badge/challenge admin tests, settings tests, `test_admin_user_premium*` if present) → green. App imports.
- [ ] **Step 5:** Commit `refactor(admin): extract admin_gamification + admin_settings`.

---

### Task 5: Extract `admin_media.py` + reduce `admin.py` to aggregator + full verify

**Files:** Create `admin_media.py`; Modify `admin.py`, `backend/tests/test_video_assets_admin.py`.

- [ ] **Step 1:** Create `admin_media.py` (`router = APIRouter()`). Move video-health + video-health/check + video-assets/presign + the `_video_health_items` helper (uses `storage`), with imports. Add the `include_router` call; remove moved code from admin.py.
- [ ] **Step 2:** Update `tests/test_video_assets_admin.py`: the `import app.routers.admin as admin_mod` monkeypatch of `admin_mod.storage` → patch `app.routers.admin_media.storage` (import `app.routers.admin_media` instead, or patch by string path).
- [ ] **Step 3:** Confirm `admin.py` now contains ONLY: the imports for `get_current_admin` + the sub-router modules, the `router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])` declaration, and the `router.include_router(...)` calls (one per sub-router). No route functions, no leftover helpers. Remove every now-unused import.
- [ ] **Step 4 (full verify):** `ruff check backend/` clean over the whole dir. Run the FULL admin test set + a broad backend run via `.venv` pytest (at minimum every `tests/test_admin_*` + the 4 patched files); confirm green. `python -c "import app.main"` succeeds. Optionally diff the OpenAPI path set before/after (every `/admin/...` path must still be present) — e.g. start the app and assert the admin route count is unchanged.
- [ ] **Step 5:** Commit `refactor(admin): extract admin_media + reduce admin.py to aggregator`. Then push → watch CI (all 6 jobs; Backend job is the gate here) → green. Update `docs/MASTER-BACKLOG.md` (mark the admin god-router split done). No Vercel/web deploy needed (backend-only; Railway auto-deploys on green CI — and per the standing rule, this has NO DB migration so no snapshot question).

---

## Notes for the executor

- This is a pure move-refactor: read the function bodies from `admin.py` and relocate them verbatim. The risk is missed/unused imports (ruff catches these) and the 4 test patch-paths (named above).
- Sub-routers must NOT declare their own `prefix`/`dependencies` — the aggregator supplies both; declaring them again double-runs `get_current_admin`.
- After every task the app must import and start; never leave a route both moved and still defined in admin.py (duplicate path → startup or behavior error).
- Backend-only change: Railway deploys on green CI; the frontend/Vercel is untouched.
