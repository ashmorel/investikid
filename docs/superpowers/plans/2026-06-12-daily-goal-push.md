# Daily Goal + Server Push (M7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. (This run: executed inline by the controller, TDD + commit per task.)

**Goal:** Per `docs/superpowers/specs/2026-06-12-daily-goal-push-design.md` — 7a daily goal loop end-to-end; 7b push foundation (FCM) with safe no-ops until operator setup.

### Task 1 (7a): migration + xp_service seam
- [ ] Migration (one for all M7 columns): `user_progress` += `daily_goal_xp` int NOT NULL server_default '30', `xp_today` int NOT NULL server_default '0', `xp_today_date` date NULL, `last_push_sent_date` date NULL; `users` += `push_enabled` bool NOT NULL server_default 'false'; new `push_devices` table (id uuid pk, user_id FK CASCADE indexed, platform varchar(10), token varchar(255) unique, created_at, last_seen_at).
- [ ] `app/services/xp_service.py: record_xp(progress, amount, *, today) -> XpResult(goal_met_now, goal_met_today)`; route content `_award_completion` + both `simulator_rewards` sites through it.
- [ ] Tests: window reset, goal_met_now once, all award sites bump xp_today.
- [ ] Commit `feat(m7): daily-goal columns + record_xp seam`.

### Task 2 (7a): goal API + completion flag
- [ ] `UserProgressOut` += daily_goal_xp, xp_today, goal_met; `PATCH /users/me/goal` ({10,30,50}); `LessonCompletionResult` += `daily_goal_met` (true only when this completion flipped it); `ChildAnalyticsOut` += daily_goal_xp, xp_today.
- [ ] Tests: progress payload, PATCH validation/auth, completion flips once, parent analytics fields.
- [ ] Commit `feat(m7): daily goal API surface`.

### Task 3 (7a): StatsCard goal bar + ProfileMenu picker + toast
- [ ] StatsCard row 2 = daily-goal progress bar (xp_today/daily_goal_xp, met state + aria-live, tier emoji rules); level caption row 3 keeps level maths.
- [ ] ProfileMenu "Daily goal" picker (Chill 10 / Steady 30 / Super 50 → PATCH, optimistic update).
- [ ] Lesson completion toast line when response `daily_goal_met` (reuse reward-toast pattern).
- [ ] Tests + axe both tiers; update Home/StatsCard tests.
- [ ] Commit `feat(m7): daily goal UI (bar, picker, goal-met toast)`.

### Task 4 (7b): push devices + parent switch
- [ ] `app/models/push_device.py` + registration endpoints (`POST/DELETE /users/me/push-devices`, upsert by token); `/users/me` exposes `push_enabled`; parent toggle `POST /parent/children/{id}/push` (audited, IDOR-safe, mirrors freeze toggle); ChildOut += push_enabled.
- [ ] Tests: upsert/delete/auth; parent toggle matrix.
- [ ] Commit `feat(m7): push device registry + parent master switch`.

### Task 5 (7b): push_service + streak-risk cron + analytics
- [ ] `push_service.send_to_user` (firebase-admin lazy import; unconfigured → logged no-op; invalid token → delete device; sets `last_push_sent_date`); `push_sent` in SERVER_EVENTS.
- [ ] `streak_risk_push.run(session, today)` selection per spec + `/internal/push-streak-risk/run` (CSRF-exempt list + cron workflow step).
- [ ] Tests: cap, no-op, cleanup, selection in/out, event recorded, endpoint guards.
- [ ] Commit `feat(m7): push service + streak-at-risk cron`.

### Task 6 (7b): client push lib + toggles
- [ ] `npm i @capacitor/push-notifications`; `src/lib/push.ts` gating matrix (native && parent && child toggle) — dynamic import so web bundles stay clean; ProfileMenu child toggle (replaces/extends the local-reminder toggle section); ChildCard parent switch.
- [ ] Tests: gating matrix (plugin mocked), toggles.
- [ ] Commit `feat(m7): client push registration + consent toggles`.

### Task 7: verify + push + docs
- [ ] Full gates both stacks; cap sync ios (note: NEW PLUGIN → USER Xcode rebuild required; push capability/entitlement + Firebase = operator steps); CI green; roadmap/memory.
