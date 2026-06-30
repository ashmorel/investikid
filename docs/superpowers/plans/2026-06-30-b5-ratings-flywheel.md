# B5 — Ratings & reviews flywheel — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. TDD. Checkbox steps.

**Why:** The single most direct lever on the App Store / Play **star rating** — and currently
nobody asks. Fire the **native OS in-app-review prompt** at a *delight moment* (a 7-day streak
milestone OR a level mastery), self-rate-limited so it's never spammy or ill-timed.

**Decisions locked (AD-B5):**
- **Trigger:** a **7-day streak milestone** (streak just advanced to a multiple of 7) **OR a level
  mastery** (`record_mastery_if_earned` returned a new row on this completion). Whichever fires
  first wins; the cooldown guarantees we ask at most once.
- **Cooldown:** ask **at most once per 60 days**, **never in the first session**, and **never**
  after a wrong answer / paywall / error. The OS also throttles — we only pick the *moment*.
- **Plugin:** `@capacitor-community/in-app-review` v8 (free, Capacitor-8 compatible, native dialog
  on both platforms). **No custom Swift/Kotlin** — off-the-shelf `InAppReview.requestReview()`.

**Architecture:** Backend adds two booleans-ish signals to the lesson-completion response so the
client knows a delight moment happened *on this completion*. The client gate (native-only +
cooldown + not-first-session) decides whether to call the native prompt, and records the ask.

**Ships INERT on web** (the prompt is native-only → `requestReview()` is a no-op off-device). The
backend fields are harmless additions. So this lands on `main` now (backend + web bundle) and
**activates on devices at the next native build** — batched with B6 + the queued diagnostic copy
fix. **No version bump / `cap sync` in this plan** (that happens once, after B6).

## Global Constraints
- Kids' app, WCAG 2.2 AA. No `as any`; i18n if any visible string (the native prompt has none).
- Never read/modify `.env`. Backend `ruff` clean; frontend tsc/lint/test/build green. venv
  `/Users/leeashmore/Local Repo/.venv`.
- Commit to branch `b5-ratings-flywheel`; body ends
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. **No DB migration** (schema-only
  additions to a Pydantic response model — no DB change).

## File Structure
- `backend/app/schemas/content.py` — add fields to `LessonCompletionResult` (modify).
- `backend/app/routers/content.py` — capture milestone + mastery, populate the result (modify).
- `frontend/package.json` — add `@capacitor-community/in-app-review` (modify).
- `frontend/src/lib/inAppReview.ts` — thin wrapper: `maybeRequestReview(signal)` (new).
- `frontend/src/lib/inAppReviewCooldown.ts` — localStorage cooldown + first-session guard (new).
- `frontend/src/pages/child/Lesson.tsx` — call the gate in the complete-mutation `onSuccess` (modify).
- Tests alongside each.

---

### Task 1: Backend — surface the delight signals on completion

Context: `record_mastery_if_earned(...)` (called at `content.py:395`) returns `LevelMastery | None`
— **non-None means a level was just mastered on this call**. Streak is updated via
`record_daily_activity` (STREAK_MILESTONE = 7, `streak_config.py`). The completion result is built
at `content.py:449`.

- [ ] **Step 1 (test first):** in the lesson-completion tests —
  - completing a lesson that advances the streak to a multiple of 7 → `streak_milestone_reached == 7`
    (and `14` at fourteen, etc.).
  - a same-day repeat completion at an already-multiple-of-7 streak → `streak_milestone_reached is None`
    (milestone must be **newly reached** this completion, not merely "currently a multiple of 7").
  - completing the final lesson of a level that passes → `level_mastered is True`; otherwise `False`.
  - an `already_completed` replay → both signals falsy (no re-trigger).
  Run → fail.
- [ ] **Step 2:** add to `LessonCompletionResult`: `streak_milestone_reached: int | None = None` and
  `level_mastered: bool = False`. In the endpoint: snapshot `prev_streak = progress.streak_count`
  **before** the activity/award step; after, compute
  `milestone = new_streak if (not already and new_streak > prev_streak and new_streak % STREAK_MILESTONE == 0) else None`.
  Capture the `record_mastery_if_earned(...)` return (already called at :395) into a variable and set
  `level_mastered = mastery is not None`. Pass both into `LessonCompletionResult(...)`.
- [ ] **Step 3:** backend tests green; `ruff` clean. (No migration.)

### Task 2: Frontend — plugin + cooldown gate (the decision logic, unit-tested)

- [ ] **Step 1 (test first):** `inAppReviewCooldown.test.ts` —
  - `shouldAskForReview()` → true when never asked; false within 60 days of the last ask; true after.
  - `recordReviewAsked()` persists a timestamp (localStorage); tolerant of private-mode throw.
  - first-session guard: `shouldAskForReview()` → false until a "seen a prior session" flag is set
    (`markSessionSeen()` on app boot; the very first session never asks).
  Run → fail.
- [ ] **Step 2:** `npm i @capacitor-community/in-app-review`. Create `inAppReviewCooldown.ts`
  (localStorage keys `ik:iar:lastAsked`, `ik:iar:seen`; 60-day constant; try/catch). Create
  `inAppReview.ts` exporting `maybeRequestReview(signal: 'streak' | 'mastery'): Promise<void>` that:
  (a) returns early if `!Capacitor.isNativePlatform()`; (b) returns early unless `shouldAskForReview()`;
  (c) `await InAppReview.requestReview()` then `recordReviewAsked()`; (d) swallows any error (never
  throws into the lesson flow). Unit-test `maybeRequestReview` with the plugin + `Capacitor` mocked:
  native + cooldown-ok → calls `requestReview` once + records; web platform → never calls; within
  cooldown → never calls.
- [ ] **Step 3:** tsc/lint/test green. Call `markSessionSeen()` once at app startup (where the app
  boots — e.g. the root App effect); a tiny, covered addition.

### Task 3: Frontend — wire the trigger into lesson completion

- [ ] **Step 1 (test first):** in `Lesson.tsx` tests (or a focused test) — on the complete-mutation
  `onSuccess`, when the result has `streak_milestone_reached` (truthy) **or** `level_mastered` and
  `!already_completed`, `maybeRequestReview` is called (once) with the right signal; when neither
  flag is set, or on `already_completed`, it is **not** called. Mock `maybeRequestReview`. Run → fail.
- [ ] **Step 2:** in `Lesson.tsx` `onSuccess` (~line 93), after the existing celebratory logic, add the
  guarded call: prefer `streak` when a milestone is present, else `mastery`. Fire-and-forget (don't
  block the UI; it's already async-swallowed).
- [ ] **Step 3:** tsc/lint/test/build green.

### Task 4: Verify + ship (no native build yet)
- [ ] Backend `ruff` + diagnostic/content suites (isolated); frontend gates. Per-task sonnet reviews
  (Tasks 1–3) → opus whole-branch review → green CI → Railway (backend) + manual Vercel (web).
  **No migration → no snapshot ask. No version bump / `cap sync`** — B5 activates on-device at the
  next native build, batched with B6 + the diagnostic copy fix.
- [ ] Update `MASTER-BACKLOG` (B5 shipped, native-activation pending) + the native-build handoff doc's
  "pending native-visible changes" list (add B5).

## Out of scope
- B6 streak beats, B1 focus, B3 arcade rule (separate items).
- A "strong daily-goal run" trigger (the spec's third option) — keep the trigger set to streak +
  mastery for now; can add later behind the same gate.
- Custom native review plugin (using the community plugin instead).
- Any web fallback prompt (no "rate us" web UI — native-only by design).
