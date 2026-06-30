# B6 — Streak emotional beats — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Why:** The streak engine is Duolingo-grade but spends its best moments silently. Three cheap,
high-dopamine beats: (1) celebrate when a **freeze saves a streak**, (2) make freezes **visible**
(held count + next-freeze countdown), (3) let a child **spend earned coins to repair a just-broken
streak** (on-theme, no real money).

**Decisions locked (AD-B6):**
- **Explicit `freeze_used` signal** on the lesson-completion response (don't make the client guess).
- **Repair window + cost:** repair is offered when the streak has just lapsed — last activity
  **2–3 days ago** (gap ∈ {2,3}) AND the would-reset streak was **≥ 3 days** — and costs a flat
  **50 coins**. Gap 1 = still alive (no repair). Gap 2 *with a freeze held* = auto-saved (no repair).
  Gap ≥ 4 = too late. All tunables live in `streak_config.py`.
- **No migration** — eligibility + the "bridge" are computed from existing fields
  (`last_activity_date`, `streak_count`, `streak_freezes`, `virtual_coins`). Repair sets
  `last_activity_date = today − 1` so the next activity continues the streak (`streak_count` preserved).

**Architecture / seams (grounded):**
- Streak math: `streak_after_activity` / `record_daily_activity` in `app/services/content_service.py`
  (freeze consumed when `gap == STREAK_FREEZE_GAP (=2)` and `freezes > 0`). `record_daily_activity`
  has **4 callers** (content/simulator/moneyword/revise) → **do NOT change its signature**.
- Completion result built at `app/routers/content.py:449`; `prev_streak` already snapshotted at :377.
- Progress status: `GET /users/me/progress` → `UserProgressOut` (`app/routers/users.py:105`,
  `app/schemas/user.py:111`).
- Coin spend pattern: `progress.virtual_coins = coins - cost` (see `app/routers/cosmetics.py:167`).
- Streak UI: `frontend/src/components/child/StatsCard.tsx`; Home hosts dismissible cards
  (`ProgressCheckCard` pattern). Progress fetched via the `/users/me/progress` query.

## Global Constraints
- Kids' app, WCAG 2.2 AA, ≥44px, i18n keys, no `as any`. Backend `ruff`; frontend gates green.
- Repair is **server-authoritative**: validate window + balance server-side; never trust client.
  Idempotent (after repair, gap becomes 1 → a second call is 409). No real money — coins only.
- Never read/modify `.env`. venv `/Users/leeashmore/Local Repo/.venv`. Branch `b6-streak-beats`;
  commits end `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. **No DB migration.**
- B6 is **web-visible** (toasts/cards render on web) → activates on web at merge; also rides the next
  native build for device parity (batched with B5 + the diagnostic copy fix).

## File Structure
- `backend/app/services/streak_config.py` — add `STREAK_REPAIR_COST=50`, `STREAK_REPAIR_MAX_GAP=3`,
  `STREAK_REPAIR_MIN_STREAK=3` (modify).
- `backend/app/services/content_service.py` — `freeze_will_be_consumed(...)` + `repair_eligibility(...)`
  pure helpers (modify).
- `backend/app/schemas/content.py` — `freeze_used: bool = False` on `LessonCompletionResult` (modify).
- `backend/app/schemas/user.py` — `next_freeze_in`, `streak_repair_available`, `streak_repair_cost`
  on `UserProgressOut` (modify).
- `backend/app/routers/content.py` — populate `freeze_used` (modify).
- `backend/app/routers/users.py` — populate the new progress fields (modify).
- `backend/app/routers/streak.py` (or extend an existing router) — `POST /streak/repair` (new/modify).
- `frontend/src/api/...` — progress type + `useRepairStreak()` mutation (modify).
- `frontend/src/pages/child/Lesson.tsx` — "Streak saved!" toast on `freeze_used` (modify).
- `frontend/src/components/child/StatsCard.tsx` — freeze count + next-freeze countdown (modify).
- `frontend/src/components/child/StreakRepairCard.tsx` — Home repair offer (new) + wire on Home (modify).
- i18n keys; tests alongside.

---

### Task 1: Backend — `freeze_used` celebration signal
- [ ] **Step 1 (test first):** pure `freeze_will_be_consumed(last, freezes, today)` returns True only
  when `last is not None and last != today and (today-last).days == STREAK_FREEZE_GAP and freezes > 0`.
  Endpoint: completing a lesson that bridges exactly one missed day with a freeze held →
  `freeze_used is True`; a normal consecutive day → False; a same-day repeat / `already_completed` →
  False. Run → fail.
- [ ] **Step 2:** add the helper; add `freeze_used: bool = False` to `LessonCompletionResult`; in the
  completion handler snapshot the freeze condition **before** `_award_completion` and set
  `freeze_used = (not already) and freeze_will_be_consumed(prev_last, prev_freezes, today)`.
- [ ] **Step 3:** backend tests green; `ruff` clean.

### Task 2: Backend — freeze countdown + coin-funded repair
- [ ] **Step 1 (test first):**
  - `repair_eligibility(progress, today)` (pure) → eligible when `gap ∈ {2,3}`, the streak WOULD reset
    on next activity (i.e. NOT auto-saved by a held freeze at gap 2), and `streak_count ≥ STREAK_REPAIR_MIN_STREAK`;
    not eligible for gap 1 / gap ≥ 4 / streak < 3 / `last is None`. Returns the restorable streak + cost.
  - `GET /users/me/progress` includes `next_freeze_in` (= `STREAK_MILESTONE - streak_count % STREAK_MILESTONE`,
    clamped sensibly), `streak_repair_available`, `streak_repair_cost`.
  - `POST /streak/repair`: eligible + enough coins → deducts `STREAK_REPAIR_COST`, sets
    `last_activity_date = today - 1` (streak_count preserved), 200 + updated progress. Not eligible → 409.
    Insufficient coins → 409 (clear detail). A second immediate call → 409 (gap now 1). Auth required.
  Run → fail.
- [ ] **Step 2:** implement the constants, helpers, the `UserProgressOut` fields, and the
  `POST /streak/repair` endpoint (admin not required — it's the child's own progress; `get_current_user`).
  **CSRF:** it's a state-changing POST — ensure it works with the app's CSRF setup like other child POSTs.
- [ ] **Step 3:** backend tests green; `ruff` clean. (No migration.)

### Task 3: Frontend — celebration, visibility, repair offer
- [ ] **Step 1 (test first):**
  - Lesson `onSuccess`: when `result.freeze_used`, a "Streak saved!" toast fires (mock toast); not
    otherwise. (Keep B5's review call intact.)
  - `StatsCard`: renders held freeze count and "next freeze in N days" from progress.
  - `StreakRepairCard`: shows only when `streak_repair_available`; clicking confirm calls the repair
    mutation; hidden otherwise. vitest-axe clean; ≥44px.
  Run → fail.
- [ ] **Step 2:** progress type + `useRepairStreak()` (POST `/streak/repair`, invalidates the progress
  query + coins). Lesson toast on `freeze_used`. StatsCard freeze visibility. `StreakRepairCard` on Home
  (dismissible, like `ProgressCheckCard`). i18n keys; no `as any`; ≥44px.
- [ ] **Step 3:** tsc/lint/test(+axe)/build green.

### Task 4: Verify + ship
- [ ] Backend `ruff` + content/streak/users suites (isolated); frontend gates. Per-task sonnet reviews →
  opus whole-branch review → green CI → Railway (backend) + manual Vercel (web). **No migration → no
  snapshot ask.** B6 is web-live at merge; add it to the native-build handoff "pending" list (rides the
  next build with B5 + the diagnostic copy fix; no extra `cap sync` dep beyond B5's).
- [ ] Update `MASTER-BACKLOG` (B6 shipped) + memory.

## Out of scope
- Surfacing `freeze_used` celebrations on the simulator/moneyword/revise activity paths (lesson only
  for now; the helper is reusable later).
- Streak repair via real money (coins only, ever).
- Changing the freeze earn cadence or cap (B6 only surfaces what exists).
