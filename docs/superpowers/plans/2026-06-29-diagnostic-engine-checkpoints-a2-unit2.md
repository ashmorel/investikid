# A2 Unit 2 — Diagnostic Engine + MasteryCheckpoint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Goal:** The measurement core — a child runs a short diagnostic over their in-scope
topics, and the result is stored as an **immutable `MasteryCheckpoint`** snapshot. Comparing
the `baseline` checkpoint to the latest `progress` checkpoint yields the evidence headline
(*"mastery +X% after Y sessions"*). Consumes ONLY `approved` `DiagnosticItem`s (Unit 1).
Spec: `docs/superpowers/specs/2026-06-29-mastery-measurement-a2-a3-design.md`.

**Architecture:** `start` selects approved items for the child's in-scope topics (OD1:
`topic_path` + budgeting/savings/risk), 1–2 per topic, difficulty-balanced, **unseen-first**
(N3), creates a `DiagnosticSession` (records the item ids, bumps each item's `times_shown`),
and returns the items **without** answers. `submit` scores server-side (the child never sees
`answer_index`), writes an immutable `MasteryCheckpoint` + per-topic rows, bumps
`times_correct` on correct items (calibration), and warm-starts `TopicMastery` (N2 — the
evidence axis stays separate from `TopicMastery`'s live signal). `evidence` returns
baseline→latest deltas (the A4 seam). **Diagnostic answers NEVER award XP/streak/coins.**

**Tech Stack:** FastAPI · SQLAlchemy async · Alembic · pytest.

## Global Constraints

- **Approved-only:** selection queries `DiagnosticItem.status == "approved"` and market scope
  ONLY. A draft/retired item can never appear in a diagnostic.
- **Graceful empty:** if there are no approved items for the child's scope, `start` returns
  an **empty session** (no items) and the flow resolves to a `kind="skipped"` checkpoint —
  it must NEVER crash or 500. This is the expected state until the operator approves items.
- **Server-authoritative scoring:** `answer_index` is never sent to the client; `submit`
  scores against the session's stored items. A submit can only answer items in its session.
- **Immutable checkpoints:** a `MasteryCheckpoint` is written once and never mutated.
- **No reward side-effects:** the diagnostic path must not call `record_daily_activity` /
  `award_xp` / coins / streak. It is wholly separate from `/lessons/{id}/complete`.
- **Market-scoped + rate-limited** endpoints. All under the child's authenticated identity
  (`get_current_user`); no field can cross to another user.
- Backend `ruff` clean. Commit to branch `diagnostic-engine`; body ends
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. venv `/Users/leeashmore/Local Repo/.venv`.
  Never read/modify `.env`. **DB migration:** additive tables; check `alembic heads`
  (expected `9a8b7c6d5e4f`), chain from it, VERIFY a unique revision id (grep first — an
  id-collision bit this project once). Ship task asks the operator about a prod snapshot.

## File Structure
- `backend/app/models/mastery.py` — `MasteryCheckpoint`, `MasteryCheckpointTopic`, `DiagnosticSession` (new).
- `backend/alembic/versions/<rev>_mastery_checkpoints.py` — migration (new).
- `backend/app/schemas/diagnostic_session.py` — start/submit/evidence schemas (new).
- `backend/app/services/diagnostic_service.py` — selection + start + submit + evidence (new).
- `backend/app/routers/diagnostic.py` — `/diagnostic/*` endpoints (new), mounted in the app.
- Tests alongside.

---

### Task 1: Models + migration

**Fields:**
- `MasteryCheckpoint`: `id`, `user_id` (FK, indexed), `market_code` (str8), `kind` (str12: baseline/progress/skipped), `session_count` (int default 0), `overall_score` (float|None — fraction 0..1), `taken_at` (tz dt, server_default now).
- `MasteryCheckpointTopic`: `id`, `checkpoint_id` (FK→mastery_checkpoints, ondelete CASCADE), `topic` (str30), `correct` (int), `attempted` (int).
- `DiagnosticSession`: `id`, `user_id` (FK, indexed), `market_code` (str8), `kind` (str12), `item_ids` (JSON list[str]), `created_at` (tz dt), `completed_at` (tz dt|None).

- [ ] **Step 1 (test first):** `test_mastery_models.py` — create a checkpoint + topic rows + a session; defaults (`kind`, `session_count=0`, `overall_score`/`completed_at` None); `item_ids` round-trips a list; cascade on checkpoint→topic. Run → fail.
- [ ] **Step 2:** Models (mirror `models/diagnostic.py`/`concept.py` style); register in `app/models/__init__.py`.
- [ ] **Step 3:** `alembic heads` → confirm `9a8b7c6d5e4f`; grep-verify a fresh unique revision id; hand-write additive `create_table` ×3 + indexes (`user_id` on checkpoint + session); clean reversible `downgrade`; `alembic upgrade head`; single head.
- [ ] **Step 4:** model tests green; `ruff` clean.

### Task 2: Item selection + `start`

**Interface:** `async def start_diagnostic(session, user, *, kind) -> DiagnosticSession + items` —
1. In-scope topics = `{budgeting, savings, risk}` ∪ (`user.topic_path` if set & valid).
2. Market = `active_market(user)`.
3. For each in-scope topic: select up to 2 **approved** items in that market, preferring
   difficulties not yet covered and items **unseen** by this user (unseen = not in any prior
   completed `DiagnosticSession.item_ids` for this user — N3); if the bank is thin, fall back
   to seen items and **log a caveat**. Cap total ~8–10.
4. Create a `DiagnosticSession(item_ids=[...])`; bump each selected item's `times_shown`.
5. Return the session id + the items as `{id, topic, difficulty_tier, question, choices}` —
   **NO `answer_index`, NO explanation.**
- **Empty path:** zero approved items in scope → create a session with `item_ids=[]` and
  return empty; the caller can immediately `submit` it to a `skipped` checkpoint.

**Endpoint:** `POST /diagnostic/start` (`get_current_user`, rate-limited) → `{session_id, items: [...]}`.

- [ ] **Step 1 (test first):** `test_diagnostic_start.py` — seeds approved items across topics + an unrelated draft/retired item; assert start returns only approved in-scope items, no `answer_index` in the payload, `times_shown` bumped, a session row created with the right item_ids; **unseen-first** (a prior completed session's items are de-prioritised); **empty path** when no approved items (session with `item_ids=[]`, no crash); unauth → 401. Run → fail.
- [ ] **Step 2:** Implement selection + start + endpoint. Reuse `active_market`. Deterministic-ish ordering for tests.
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 3: `submit` (scoring + checkpoint + calibration + warm-start)

**Interface:** `async def submit_diagnostic(session, user, *, session_id, answers: dict[item_id,int]) -> MasteryCheckpoint` —
1. Load the `DiagnosticSession`; **must belong to `user` and not be completed** (else 409/404).
2. For each item in the session: look up its `answer_index` (server-side); a correct answer
   = `answers[item_id] == answer_index`. Tally per-topic `correct`/`attempted` and overall.
   Unanswered items count as attempted-incorrect (or are excluded — pick one, document it;
   *lean: count as attempted so the denominator is the session size*).
3. Write an immutable `MasteryCheckpoint(kind, overall_score=correct/attempted or None when
   attempted==0, session_count)` + `MasteryCheckpointTopic` rows. An **empty** session →
   `kind="skipped"`, `overall_score=None`, no topic rows.
4. Bump `times_correct` on each correctly-answered item (calibration).
5. **Warm-start `TopicMastery`** for the in-scope topics from the per-topic results (N2 —
   for personalization only; the evidence claim uses checkpoints, not `TopicMastery`).
6. Mark the session `completed_at`. **No XP/streak/coins.**

`session_count`: store the value provided (baseline path passes 0). The precise "active days"
source for `progress` checkpoints is finalized in Unit 4; Unit 2 just persists what it's given.

**Endpoint:** `POST /diagnostic/submit` (`get_current_user`, rate-limited) → the checkpoint summary.

- [ ] **Step 1 (test first):** `test_diagnostic_submit.py` — a fully-correct submit → `overall_score==1.0` + per-topic rows; a mixed submit scores correctly; an empty session → `kind="skipped"`, no topic rows, `overall_score None`; `times_correct` bumped only on correct items; `TopicMastery` warm-started; submitting someone else's session → 403/404; submitting a completed session → 409; **assert NO XP/streak change** (progress unchanged). Run → fail.
- [ ] **Step 2:** Implement. Reuse `TopicMastery` upsert (look at `skill_profile_service`); do NOT touch the reward/activity paths.
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 4: `evidence` endpoint + graceful states

**Interface:** `GET /diagnostic/evidence` (`get_current_user`) → for the user: the `baseline`
checkpoint (or skipped/none), the latest `progress` checkpoint, per-topic + overall **deltas**
(`latest.overall − baseline.overall`), and `session_count`. Missing baseline → `{has_baseline: false}`; baseline-only → baseline with `delta: null`.

- [ ] **Step 1 (test first):** `test_diagnostic_evidence.py` — no checkpoints → `has_baseline false`; baseline-only → no delta; baseline + a later progress → correct per-topic + overall deltas; a `skipped` baseline is reported as skipped (no scores). Run → fail.
- [ ] **Step 2:** Implement (read-only aggregation over the user's checkpoints).
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 5: Verify + ship
- [ ] Backend `ruff` + full `pytest`; single alembic head. Confirm the empty-bank path is exercised end-to-end (start→submit→skipped) and that NO diagnostic path mutates XP/streak/coins.
- [ ] Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. **Ask the operator about a prod snapshot before the migration.** SDD finishing flow → green CI → Railway. Backend-only (no web/native in this unit; A3/Unit 3 adds the child UI).

## Out of scope (later units)
- **Unit 3 / A3** — the onboarding placement UI + when `start`/`submit` fire on first run + the friendly results screen (this unit ships the engine + endpoints; the child-facing flow is Unit 3).
- **Unit 4** — the session-milestone re-check trigger (+ the active-days source for `session_count`).
- **Unit 5** — per-concept rolling mastery scoring.
- **Unit 6 / A4** — the parent-report growth block + public evidence page (this unit ships the `/diagnostic/evidence` data seam only).
