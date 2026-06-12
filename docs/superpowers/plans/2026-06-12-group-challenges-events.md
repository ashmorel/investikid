# Group Challenges + Seasonal Events (M9) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Per `docs/superpowers/specs/2026-06-12-group-challenges-events-design.md` — co-op group challenges on the existing challenge engine + AppSetting-driven seasonal events with lesson-XP bonus.

### Task 1: migration + group-challenge engine
- [ ] Migration off `c0d1e2f3a4b5`: `challenges.scope` (String(10), NOT NULL, server_default 'personal') + `group_challenge_completions` table. Validate with scratch-Postgres full-chain replay BEFORE pushing.
- [ ] Models: `Challenge.scope`, new `GroupChallengeCompletion` (registered in models __init__).
- [ ] Engine: `update_challenge_progress` — group-scope branch per spec (skip personal completion; group-sum; SAVEPOINT completion row; reward members once via `record_xp`).
- [ ] Tests: personal unchanged, group sum/threshold, once-only rewards, multi-group, late joiner.
- [ ] Commit.

### Task 2: child API + Stats UI + admin scope field
- [ ] `GET /groups/challenges` in groups router + schemas.
- [ ] Stats page group-goal block (progress bar, completed state, tier emoji rules) + tests + axe.
- [ ] Admin ChallengeForm scope select + ChallengeList chip (+ schema/router accept scope).
- [ ] Commit.

### Task 3: seasonal events
- [ ] `event_service.get_active_event`; `GET /events/active` (child); `AdminSettingsUpdate.seasonal_event` validation + AdminSettings UI section.
- [ ] `complete_lesson` bonus application (`_award_completion(amount)`); Home event strip (active-only, tier-aware).
- [ ] Tests per spec matrix (backend + frontend + axe).
- [ ] Commit.

### Task 4: verify + ship
- [ ] Full gates both stacks (exit codes, not greps); cap sync; push; CI green; **Railway testing deploy SUCCESS + health check**; roadmap M9 done + memory.
