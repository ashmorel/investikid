# W3a — Schema + Mastery Recording + API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]` checkboxes.

**Goal:** Add the curriculum-credibility data model (standards/sources/objectives fields + auditable `level_mastery` records), record mastery automatically on lesson completion, backfill existing passers, and expose the new fields through child/parent/admin APIs.

**Architecture:** One chained Alembic migration (head: `3737143bb340`) adds 3 nullable JSON columns + the `level_mastery` table + a data backfill. A small `mastery_service` reuses `level_service._complete_and_passed` so "mastered" is *identical* to the existing "passed" semantics — recorded once, on the completion path in `routers/content.py` (`_award_completion` callers). Schemas gain the new fields.

**Spec:** `docs/superpowers/specs/2026-06-10-curriculum-credibility-design.md` (W3a = sub-project 1).

**Verify:** `/Users/leeashmore/Local Repo/.venv/bin/ruff check .` + `pytest` from `backend/`. Branch `testing`; explicit `git add` only; commit suffix `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. No promotion. Async tests: `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`db_session` fixtures.

**Key verified facts for implementers:**
- Models: `backend/app/models/content.py` — `Module` (no standards/sources), `Level` (`pass_threshold` Float 0.7), `LessonCompletion` (user_id, lesson_id unique pair, `score` Float|None).
- Pass semantics: `backend/app/services/level_service.py::_complete_and_passed(lesson_ids, completed_ids, scores, threshold)` → `(complete, passed)`; passed = all lessons complete AND avg of non-None scores ≥ threshold (no scored lessons → passed on completion). **Mastery must reuse this function.**
- Completion path: `backend/app/routers/content.py::_award_completion` (~line 350) inserts/updates `LessonCompletion` with best-score-wins + nested-transaction race handling. The mastery hook goes in the endpoint that calls it, AFTER the completion flush, with access to `session`, `user_id`, and `lesson` (lesson has `level_id`).
- Migration chain head: `3737143bb340` (run `alembic heads` to confirm before writing). Follow existing migration style (`sa.Uuid`/UUID(as_uuid=True), JSON columns as in prior migrations).
- Schemas: `backend/app/schemas/content.py` — `ModuleOut` (~15), `LevelOut` (~67); parent: `backend/app/schemas/parent.py` — `ModuleProgressOut`, `LevelProgressOut`. Admin update schemas in `backend/app/schemas/admin.py`.

---

### Task 1: Models + migration + backfill
**Files:** Modify `backend/app/models/content.py`; Create `backend/alembic/versions/<rev>_curriculum_credibility.py`; Test `backend/tests/test_level_mastery_model.py`
- [ ] Add `Module.standards_alignment: Mapped[list | None]` (JSON, nullable) and `Module.sources` (JSON, nullable); `Level.learning_objectives` (JSON, nullable); new `LevelMastery` model (`level_mastery`: id UUID PK, user_id FK users CASCADE, level_id FK levels CASCADE, mastered_at timestamptz not null, score Float not null, UniqueConstraint(user_id, level_id)).
- [ ] Write the chained migration (down_revision = current head). Upgrade: add 3 columns + table + unique constraint; **backfill**: for each (user, level) where the level's lessons are all completed by that user and avg(non-null scores) ≥ pass_threshold (no scored → mastered on completion), insert a `level_mastery` row with `mastered_at = max(completed_at)` of that level's completions and `score` = the computed avg (or pass_threshold when no scored lessons). Implement backfill in raw SQL or SQLAlchemy core within the migration (no ORM model imports). Downgrade drops table + columns.
- [ ] Tests: model round-trip + unique constraint; `alembic upgrade head` runs in the test DB (the suite's migrated schema includes the new objects).
- [ ] `ruff` + targeted pytest green → commit (`feat(w3a): curriculum-credibility schema + level_mastery + backfill`).

### Task 2: Mastery service + completion hook
**Files:** Create `backend/app/services/mastery_service.py`; Modify `backend/app/routers/content.py`; Test `backend/tests/test_level_mastery_recording.py`
- [ ] `async def record_mastery_if_earned(session, user_id, level_id) -> LevelMastery | None`: load the level + its lesson ids; load the user's completions/scores for those lessons; call `level_service._complete_and_passed`; if passed and no existing row → insert (race-safe: nested begin + IntegrityError pass, mirroring `_award_completion`'s pattern); return the row or None. Never update/delete existing rows.
- [ ] Hook: in the lesson-completion endpoint after `_award_completion` succeeds and the lesson has a `level_id`, call `record_mastery_if_earned`. Must not change XP/streak/response behaviour (optionally add `mastered_now: bool` to the completion response ONLY if a response schema change is trivial; otherwise skip — W3c can read mastered_at from LevelOut).
- [ ] Tests: not mastered while lessons incomplete; mastered exactly at threshold; below threshold → no row; second qualifying completion → still one row; best-score upgrade later does NOT rewrite `mastered_at`; card-only level masters on completion; race idempotency.
- [ ] `ruff` + pytest → commit (`feat(w3a): record level mastery on completion`).

### Task 3: API exposure (child + parent + admin)
**Files:** Modify `backend/app/schemas/content.py`, `backend/app/schemas/parent.py`, `backend/app/schemas/admin.py`, `backend/app/routers/content.py`, `backend/app/services/analytics_service.py`, admin router; Tests extend `backend/tests/test_levels_api.py`-style + analytics + admin tests.
- [ ] `ModuleOut` += `standards_alignment: list[StandardRef] | None`, `sources: list[SourceRef] | None` (new small pydantic models `{framework,code,label}` / `{title,url}`). `LevelOut` += `learning_objectives: list[str] | None`, `mastered_at: datetime | None` (per requesting user; populate in the levels endpoint with one query over `level_mastery`).
- [ ] Parent: `LevelProgressOut` += `mastered_at`; `ModuleProgressOut` += `standards_alignment`; populate in `build_child_analytics`.
- [ ] Admin: module update schema accepts `standards_alignment`/`sources`; level update accepts `learning_objectives` — validated shapes (non-empty strings; sources url must start http(s)). Existing admin auth/validation patterns.
- [ ] Tests: levels endpoint returns objectives + mastered_at (null then set after mastering); modules endpoint returns standards/sources; parent analytics includes both; admin can update + validation rejects bad shapes.
- [ ] `ruff` + pytest → commit (`feat(w3a): expose objectives/standards/mastery via child, parent, admin APIs`).

### Task 4: Seed upsert support + full regression + push
**Files:** Modify `backend/app/seed/content.py` (seeder only — content arrives in W3b); Test extend `backend/tests/test_seed_content.py`.
- [ ] Seeder: when a module spec has `standards_alignment`/`sources`, upsert onto the Module row (update-in-place like `icon`/`is_premium` today); when a level spec has `learning_objectives`, upsert onto the Level. Absent keys → leave untouched. Idempotent.
- [ ] Test: seed with a spec carrying the new keys updates rows; re-seed no-ops; specs without keys unchanged.
- [ ] Full `ruff check .` + `pytest` + push `origin testing`; report CI.

## Self-review
- Spec A (schema+backfill)=T1, B (recording)=T2, C (API)=T3, seed plumbing for E=T4. W3b/W3c are separate plans.
- Mastery reuses `_complete_and_passed` — no parallel semantics. Backfill decision (default: yes) implemented in T1.
- No FE change in W3a; no unlock-logic change; migration is chained and reversible.
