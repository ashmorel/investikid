# Group Challenges + Seasonal Events (M9) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M9 (final build workstream) of
`docs/2026-06-12-market-leader-roadmap.md`. COPPA spine unchanged: no child-initiated
social, no messaging — groups remain parent-mediated; events are admin-authored.

## 9a — Weekly co-op group challenges

**Model:** `challenges.scope` String(10) NOT NULL default `'personal'`
(`'personal' | 'group'`). New table `group_challenge_completions`
(`group_id` FK CASCADE, `challenge_id` FK CASCADE, `completed_at`, unique pair) —
records each group's crossing exactly once (race-safe SAVEPOINT insert).

**Engine** (`update_challenge_progress`): per-user `UserChallenge.progress` accumulates
exactly as today for BOTH scopes (group totals are just the sum of members' rows). For
`scope='group'` the personal-completion branch is skipped; instead, after incrementing,
for each of the child's groups: `group_total = SUM(progress of members' rows)`; when
`group_total >= target_value` and no completion row exists → insert
`GroupChallengeCompletion` + for every member whose row isn't completed: set
`completed_at` and award `xp_reward` (via `record_xp`, so coins/daily-goal ride along).
A child in multiple groups contributes to each; a member is rewarded at most once per
challenge (their `completed_at` is the guard).

**Child API:** `GET /groups/challenges` → per joined group, the active group-scope
challenges: `{group_id, group_name, challenges: [{id, title, description, emoji?,
target_value, group_progress, completed, ends_at}]}`.

**UI:** Stats page, inside/next to the existing `GroupLeaderboard`: a "Group goal" block
per active challenge — progress bar (`group_progress/target_value`), "Completed 🎉"
state (tier emoji rules), ends-at hint. Admin `ChallengeForm` gains a Scope select
(Personal / Group co-op); `ChallengeList` shows a `Group` chip.

## 9b — Seasonal events (deploy-free, AppSetting)

**Storage:** `AppSetting` key `seasonal_event` (JSON):
`{"title": "Spooky Savings Week", "emoji": "🎃", "starts_at": ISO, "ends_at": ISO,
"xp_bonus_pct": 25}`. Null/absent = no event. `app/services/event_service.py:
get_active_event(session, now) -> dict | None` (window check, defensive parsing —
malformed JSON = no event, logged).

**Admin:** `GET/PUT /admin/settings` extends `AdminSettingsUpdate` with optional
`seasonal_event` (validated: title ≤60, 0 ≤ xp_bonus_pct ≤ 100, ends_at > starts_at;
explicit `null` clears it). AdminSettings page gains a "Seasonal event" section
(fields + Clear button) — events are runnable from /admin without a deploy (the
M9 success criterion).

**Child surfaces:**
- `GET /events/active` (child session) → event payload or `{event: null}`.
- Home: a slim strip ABOVE StatsCard, rendered ONLY while an event is active
  (time-boxed, so it respects the M3 one-primary-action discipline):
  "🎃 Spooky Savings Week — +25% XP!" (investor tier: no emoji). aria-label'd,
  not a link in v1.
- **Bonus XP:** applies to lesson completions only (the learning loop): in
  `complete_lesson`, `awarded = round(xp_reward * (1 + pct/100))` passed through
  `_award_completion` (signature gains an `amount` param). The completion response's
  existing `xp_awarded` reflects the boosted number. Simulator/mission XP unboosted
  (keeps the sim economy stable).

**Special badge:** authored via the EXISTING admin badge CRUD when wanted — no new
mechanism (out of scope here).

## Migration

One migration off `c0d1e2f3a4b5`: add `challenges.scope` + create
`group_challenge_completions`. Verified against the initial schema (no collisions) and
validated by full-chain alembic replay on a scratch Postgres before push (the new
standing practice). After push: confirm the Railway testing deploy status, not just CI.

## Testing

Backend: engine — personal challenges unaffected; group challenge sums across members;
completion awards every member once (incl. the race: duplicate crossing attempt);
multi-group child; member joining after completion gets nothing; `GET /groups/challenges`
shape+auth; event_service window/malformed cases; admin settings validation (clear,
bad pct, bad window); lesson completion applies bonus (and not when no event); response
xp_awarded boosted. Frontend: Stats group-goal block (progress, completed, axe);
Home event strip (active/none/investor); AdminSettings event section; full gates.

## Out of scope

Child-visible event leaderboards · event-specific badges automation · push notifications
for events/challenges (M7 follow-up) · group chat/comments (never).
