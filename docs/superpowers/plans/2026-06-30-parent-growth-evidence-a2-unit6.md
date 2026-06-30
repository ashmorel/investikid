# A2 Unit 6 / A4 + A5 — Parent Growth Block + Public Evidence Page — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Goal:** Surface the measurement to the people who matter. **A4** adds a *growth block* to the
parent Mastery Report — each child's baseline→latest diagnostic deltas ("Stocks 40%→75% ↑")
+ the topic to focus on + a conversation prompt — so the subscription leads with evidence.
**A5** ships a public *learning-evidence page* — how mastery is measured, standards alignment,
safety/moderation, privacy posture — the trust artifact for cautious parents and the B2B school
door. This is the **last engineering piece of Theme A**; it makes the "+X%" *visible*.

**Architecture:** Extract the baseline→progress evidence aggregation (`get_evidence`) into a
reusable `compute_evidence(session, user_id)` so the per-child parent report can call it without
the child-auth endpoint. `build_mastery_report` attaches a per-child `growth` block.
`MasteryReportCard` renders it. A5 is a public, content-driven route (no auth, no new data).
**No DB migration** — reads existing `MasteryCheckpoint`.

**Tech Stack:** FastAPI · SQLAlchemy async · React 18 · pytest · vitest.

## Global Constraints

- **Additive + behaviour-preserving:** extracting `compute_evidence` must NOT change `get_evidence`'s
  output (the child `/diagnostic/evidence` contract is unchanged). The growth block is a new,
  optional field on the report (existing report fields/behaviour unchanged).
- **Honesty gate (OD4) holds:** the growth block shows a child's *own* baseline→progress delta to
  *their own parent* — that's fine. But **no public "average +X% across all kids" marketing claim**
  on A5 until beta validates the instrument; A5 describes *how* mastery is measured + the safeguards,
  NOT an unvalidated efficacy number. State methodology + standards + safety, not a results claim.
- **Per-child privacy:** the parent report already scopes to the household's children; the growth
  query must stay scoped to each child of the requesting parent — no cross-household leak.
- A5 is **public** (no auth) — must contain NO child/user data; it's static methodology/trust content.
- WCAG 2.2 AA (vitest-axe), ≥44px, i18n keys, no `as any`. Backend `ruff` clean; frontend gates green.
- Commit to branch `parent-growth-evidence`; body ends `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
  venv `/Users/leeashmore/Local Repo/.venv`. Never read/modify `.env`. Native-visible (parent card) →
  ship runs `cap sync` (or defers per operator). **No DB migration.**

## File Structure
- `backend/app/services/diagnostic_service.py` — extract `compute_evidence(session, user_id)` (modify).
- `backend/app/services/mastery_report_service.py` + `backend/app/schemas/*` — per-child `growth` block (modify).
- `frontend/src/components/parent/MasteryReportCard.tsx` (+ api/test) — render growth (modify).
- `frontend/src/pages/...` public `LearningEvidence` page + route + nav/footer link (new).
- Tests alongside.

---

### Task 1: Extract reusable `compute_evidence(session, user_id)`

- [ ] **Step 1 (test first):** assert `compute_evidence(session, user_id)` returns the SAME dict shape `get_evidence` returns today (no-baseline / skipped / baseline-only / baseline+progress) for a given user_id; and that `get_evidence(session, user)` now delegates to it (output byte-identical to before). Run → fail.
- [ ] **Step 2:** refactor `diagnostic_service.get_evidence` — pull the aggregation (identify baseline = earliest `kind in (baseline,skipped)`, latest `kind=progress`, per-topic + overall deltas, `has_baseline`/`baseline_skipped`) into `compute_evidence(session, user_id: UUID) -> dict`; `get_evidence(session, user)` calls `compute_evidence(session, user.id)`. Behaviour-preserving.
- [ ] **Step 3:** existing evidence tests + the new delegation test green; `ruff` clean.

### Task 2: Parent-report growth block

- [ ] **Step 1 (test first):** extend the mastery-report tests — `build_mastery_report` adds a per-child `growth` object: `{has_baseline, overall_delta|null, baseline_overall|null, latest_overall|null, session_count, topic_deltas:[{topic, baseline_score, latest_score, delta}], focus_topic|null}` derived from `compute_evidence(session, child.id)`. `focus_topic` = the child's lowest-scoring topic with data (reuse `_weak_topic` if it fits, else compute from the latest checkpoint). A child with no baseline → `growth:{has_baseline:false}`. Existing report fields unchanged. Scoped to the requesting parent's children only. Run → fail.
- [ ] **Step 2:** add a `GrowthBlock` (+ `TopicDelta`) schema to the parent report schemas; in `build_mastery_report`, call `compute_evidence` per child and attach `growth`. Keep all existing fields. Per-parent scoping unchanged.
- [ ] **Step 3:** tests green; `ruff` clean.

### Task 3: Frontend — growth in the Mastery Report card

- [ ] **Step 1 (test first):** `MasteryReportCard` test (mock the api) — a child with `growth.has_baseline && overall_delta != null` shows a growth section: the overall delta (e.g. "+18%"), a few top topic deltas as "Topic baseline%→latest% ↑/↓", the `focus_topic`, and a **conversation prompt** (tier/parent-friendly copy, i18n); a child with `growth.has_baseline:false` shows a gentle "baseline captured — check back after a few sessions" state, not an error; vitest-axe clean. Run → fail.
- [ ] **Step 2:** extend `MasteryReportCard.tsx` (+ the parent api type with `growth`) to render the growth section, reusing the card's existing styling/tokens; i18n keys; no `as any`; ≥44px on any control. Frame it as the report's lead value (it's the subscription pitch).
- [ ] **Step 3:** `tsc`/`lint`/vitest(+axe)/`build` green.

### Task 4: A5 — public learning-evidence page

- [ ] **Step 1 (test first):** a `LearningEvidence` page test — renders the methodology sections (how mastery is measured: pre/post diagnostic + concept taxonomy; **standards alignment** — the frameworks already on content e.g. MaPS/CCSS; **safety** — moderated, kid-safe; **privacy** — kids'-privacy posture) with no auth required and **no user data**; vitest-axe clean; all copy via i18n keys. Run → fail.
- [ ] **Step 2:** build the public page (reuse the marketing/`/try`-style public layout if one exists; else a clean standalone), a public route (e.g. `/how-we-measure`), and a footer/marketing link to it. Content is **methodology + standards + safety + privacy** — defensible, factual; **NO efficacy/"+X%" results claim** (OD4). Mark the copy `⚙️ operator-reviewable` (a code comment) so the operator can refine wording/privacy specifics before launch.
- [ ] **Step 3:** gates green.

### Task 5: Verify + ship
- [ ] Backend `ruff` + full `pytest` (run ISOLATED — the local test DB flakes under overlapping runs; CI is authoritative); frontend gates; single alembic head (unchanged — no migration). Reason end-to-end: a child with a baseline + a progress check → the parent report shows the growth delta; the public page renders for an unauthenticated visitor.
- [ ] Update `MASTER-BACKLOG`/this plan/`PROGRESS.md`. SDD finishing flow → opus whole-branch review → green CI → Railway (backend) + manual Vercel (web). Native-visible (parent card) → `cap sync` (operator batches the build). **No migration → no snapshot ask.**

## Out of scope
- Any public efficacy/results "+X%" claim (gated on beta validation per OD4).
- Re-check cadence / item bank / scoring changes (built in prior units).
- This is the last A2 unit — after it, Theme A is engineering-complete; remaining is operator content (approve items + verify sweep), the native build, and the beta.
