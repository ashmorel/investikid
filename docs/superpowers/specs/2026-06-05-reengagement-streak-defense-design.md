# Re-engagement: Streak-Freeze + Local Notifications (Design Spec)

**Date:** 2026-06-05
**Status:** Approved (design); ready for implementation plan
**Origin:** Product-review item 3, sub-project **3A** (see `docs/2026-06-05-product-review-and-backlog.md` §1, "engagement bets"). First of three engagement sub-projects (3A re-engagement → 3B social → 3C age-tier).
**Scope:** Backend (streak-freeze) + frontend (local notifications, freeze UI). No new privacy surface — notifications are on-device and opt-in; no data leaves the phone.

---

## Problem

The app has a streak (`UserProgress.streak_count` + `last_activity_date`) but no way to *defend* it and no mechanism to *pull kids back*. A single missed day resets the streak to 1, and there are no reminders anywhere in the app. These are the two highest-leverage retention mechanics and both are absent.

## Decisions (locked with the user)

- **Streak-freeze earning:** milestone-earned and free — **+1 freeze each time the streak reaches a multiple of 7**, capped at **2** held. Auto-consumed to absorb a single missed day.
- **Notifications:** **local** (Capacitor `LocalNotifications`) only — no APNs / server / device tokens. True server **push** is explicitly deferred.
- **Notification UX:** explicit **opt-in toggle** in the child settings menu, **off by default**; no auto-prompting kids. One evening "streak at risk" reminder, not spammy.
- **Defaults:** reminder fires at **18:00 local** (fallback 20:00; skip if later); freeze indicator lives in `StatsBar`; toggle lives in `ProfileMenu`.

## Non-goals

- No server push / device-token storage / backend scheduler (deferred enhancement).
- No configurable reminder time, no multiple daily nudges, no generic "come learn" notification (YAGNI — just streak-at-risk).
- No "a freeze saved your streak!" celebration animation in v1 (just the count indicator).
- No changes to XP, levels, challenges, or the leaderboard.

---

## Part 1 — Streak-freeze (backend)

### Data model + migration
Add `streak_freezes: Mapped[int]` (default `0`, not null) to the `UserProgress` model (`app/models/user.py`, the model already holding `xp`/`level`/`streak_count`/`last_activity_date`). One hand-written, chained Alembic migration (`down_revision` = current head — check `alembic heads` first) adding the column with `server_default="0"` and `nullable=False`.

### Core logic — `streak_after_activity` (in `app/services/content_service.py`)
Currently `streak_after_activity(last, current, today) -> (new_streak, new_last)`:
- `last is None` → `(1, today)`; `last == today` → `(current, today)`; gap 1 → `(current+1, today)`; else → `(1, today)` (reset).

Change signature to take and return the freeze count:
`streak_after_activity(last, current, freezes, today) -> (new_streak, new_last, new_freezes)` with these rules:
- `last is None` → `(1, today, freezes)` (first ever; no milestone at 1).
- `last == today` → `(current, today, freezes)` (no change).
- gap == 1 (consecutive day): `new = current + 1`; if `new % STREAK_MILESTONE == 0` → `freezes = min(STREAK_FREEZE_CAP, freezes + 1)`; return `(new, today, freezes)`.
- gap == 2 (exactly one day missed) **and** `freezes > 0`: consume one freeze, absorb the missed day → `new = current + 1`, `freezes -= 1`; re-check milestone on `new` (grant if `new % STREAK_MILESTONE == 0`, still capped); return `(new, today, freezes)`.
- otherwise (gap >= 2 with no freeze, or gap >= 3): reset → `(1, today, freezes)` (freezes unchanged).

Constants live in the new `app/services/streak_config.py` (`STREAK_MILESTONE = 7`,
`STREAK_FREEZE_CAP = 2`, `STREAK_FREEZE_GAP = 2`) and are imported here — see
**Configurability** below. No numeric literals inline.

> **Milestone-on-freeze edge case (made explicit):** when a freeze is consumed to reach a multiple of 7, the milestone grant still applies (net zero that day: −1 consumed, +1 earned). This is intentional and tested.

### Wiring (`app/routers/content.py`, lesson-completion path ~line 392)
Pass `progress.streak_freezes` into `streak_after_activity` and persist all three returns:
```python
new_streak, new_last, new_freezes = streak_after_activity(
    progress.last_activity_date, progress.streak_count, progress.streak_freezes, today_local
)
progress.streak_count = new_streak
progress.last_activity_date = new_last
progress.streak_freezes = new_freezes
```

### Expose
- `UserProgressOut` (`app/schemas/...` used by `GET /users/me/progress` in `app/routers/users.py`) gains `streak_freezes: int` (default 0 for the no-progress branch).
- Any other place that constructs `UserProgressOut` (e.g. the completion response in `content.py`, the no-progress branch in `users.py`) sets `streak_freezes` accordingly.
- Frontend `useProgress` type + the `Progress`/`Me` progress shape gains `streak_freezes: number`.

### Frontend UI
- `StatsBar` (`components/child/StatsBar.tsx`): render a small shield indicator next to the streak flame when `streak_freezes > 0` — e.g. `🛡️ ×{n}` with an accessible label ("N streak freezes — saves your streak if you miss a day"). Use existing semantic tokens; WCAG AA.
- Stats page: a one-line explainer of what a freeze does (near the streak/freeze display).

---

## Part 2 — Local notifications (frontend, native-only)

### Plugin
Add `@capacitor/local-notifications` to `frontend/package.json`. No APNs, no entitlement; iOS prompts for permission at runtime when first requested. After install: `npm run build && npx cap sync ios`.

### Opt-in toggle (`ProfileMenu.tsx`)
A new "Reminders" section with a **"Daily streak reminder"** toggle, **off by default**:
- Flipping ON calls `LocalNotifications.requestPermissions()`. If granted, persist the preference and (re)schedule. If denied, leave the toggle off and show a gentle inline note ("Turn on notifications for InvestiKid in Settings to get reminders").
- Flipping OFF cancels any pending reminder and clears the preference.
- Preference persisted in `localStorage` under `notif_streak_reminder` (`'1'`/absent).
- The toggle is **only shown on native** (`isNativeApp()`); hidden on web.

### Scheduling helper (`lib/streakReminder.ts`)
A pure decision function + a thin native wrapper:
- **Pure** `decideStreakReminder({ enabled, practicedToday, streakCount, now }) -> { action: 'cancel' } | { action: 'schedule', at: Date }`:
  - if `!enabled` or `streakCount <= 0` or `practicedToday` → `{ action: 'cancel' }`.
  - else compute `at`: today 18:00 local; if `now` is past 18:00 → 20:00; if past 20:00 → `{ action: 'cancel' }` (too late tonight).
- **Wrapper** `applyStreakReminder(decision)` (native-guarded): on `schedule`, `LocalNotifications.schedule` a single notification with a **fixed id** (e.g. `1001`), title/body in Penny's voice ("🔥 Keep your {n}-day streak alive!", "A quick lesson before bed keeps your streak going."); on `cancel`, `LocalNotifications.cancel({ notifications: [{ id: 1001 }] })`. No-op on web.
- **Invocation points:** a small hook `useStreakReminder()` that runs the evaluate-and-apply on app foreground (mount) and whenever `progress` changes (so completing a lesson today cancels the reminder, and opening the app while a streak is at risk schedules it). Reads `useProgress` for `streakCount` + `last_activity_date` (→ `practicedToday`) and the `localStorage` preference. Mount it once in the child shell.

### Web behaviour
All native calls are guarded by `isNativeApp()`; on web the toggle is hidden and the wrapper is a no-op. No web Notification API usage in v1.

---

## Data flow

1. **Earn:** kid completes a lesson → `streak_after_activity` increments; on a 7-multiple, `streak_freezes` rises (cap 2) → persisted → shown in `StatsBar`.
2. **Defend:** kid misses one day → next completion consumes a freeze and the streak survives; misses two+ days → resets.
3. **Reminder:** kid opens app (or completes a lesson) → `useStreakReminder` evaluates; if a streak is at risk and reminders are on, an 18:00 local notification is scheduled; completing a lesson that day cancels it.

## Error handling & edge cases

- **Permission denied / undetermined:** toggle stays off, no scheduling, gentle note shown. Re-requesting is a no-op if already denied (user must enable in iOS Settings).
- **Timezone:** "practiced today" and the 18:00 target both use the device's local date/time (consistent with the existing `today_local` used server-side for streaks).
- **App never opened that day:** no reminder fires (accepted local-notification limitation; documented; push is the deferred fix).
- **Freezes at cap:** milestone grant is a no-op (`min(cap, …)`).
- **No `UserProgress` row yet:** progress endpoint returns `streak_freezes=0`.

## Testing

**Backend (pytest, `loop_scope="session"` + `client`/`db_session`):**
- `streak_after_activity` unit matrix: first activity; same day; consecutive increment; milestone grant at 7 and 14; cap at 2; gap==2 with freeze (absorb, decrement, streak grows); gap==2 with milestone-on-freeze; gap==2 with no freeze (reset); gap>=3 (reset).
- Integration: completing lessons across simulated dates updates `streak_freezes`; `GET /users/me/progress` returns `streak_freezes`.
- Existing streak/progress/analytics tests stay green.

**Frontend (vitest + vitest-axe, Capacitor plugin mocked):**
- `decideStreakReminder` pure-function matrix (disabled, no streak, practiced today, before/after 18:00, after 20:00).
- `StatsBar` renders the shield indicator with an accessible label when `streak_freezes > 0` and omits it at 0.
- The `ProfileMenu` reminder toggle renders (native-mocked), is axe-clean, and is hidden on web.

**iOS:** `npm run build && npx cap sync ios`; **USER Xcode rebuild/TestFlight** to bundle the plugin and verify the runtime permission prompt + a scheduled reminder. Called out at close-out (no native source written by us).

## Constraints

- DB change = hand-written chained Alembic migration (check `alembic heads`). Async tests use `loop_scope="session")` + fixtures. Backend verify: `ruff` + `pytest`.
- Frontend: `npx tsc -b`, `npm run lint`, `npm test` (vitest + vitest-axe), `npm run build`. WCAG 2.2 AA; iOS inputs ≥16px, no `maximum-scale`.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway (backend) + Vercel (frontend) deploy on green CI (6 jobs). No `.env` access.

## Configurability (single source of truth for every tunable)

A hard requirement: no magic numbers or hard-coded copy scattered through the code. Every
tunable lives in one named place so it can be changed later with a single edit.

**Backend — `app/services/streak_config.py` (new, tiny module):**
```python
STREAK_MILESTONE = 7        # earn a freeze each time the streak hits a multiple of this
STREAK_FREEZE_CAP = 2       # max freezes a user can hold
STREAK_FREEZE_GAP = 2       # a gap of exactly this many days (= 1 missed day) is freezable
```
`content_service.streak_after_activity` imports these — no literals inline. Changing the
milestone interval or cap is a backend-only edit and ships with the next backend deploy
(no app release). Keep them here (not in `core/config.py`) since they're product rules, not
secrets; promoting to env-driven `Settings` later is trivial if we ever want per-env tuning.

**Frontend — `lib/reminderConfig.ts` (new):**
```ts
export const REMINDER = {
  notificationId: 1001,
  primaryHour: 18,          // first choice fire time (local)
  fallbackHour: 20,         // used if it's already past primaryHour
  storageKey: 'notif_streak_reminder',
  title: (streak: number) => `🔥 Keep your ${streak}-day streak alive!`,
  body: 'A quick lesson before bed keeps your streak going.',
} as const;
```
`streakReminder.ts`, `decideStreakReminder`, the `ProfileMenu` toggle, and the wrapper all
read from `REMINDER` — no inline times, ids, copy, or storage keys. Because these drive a
native bundle, changing them needs an app release; the config object is structured so a
future enhancement could hydrate it from a server-config endpoint without touching callers.

The `StatsBar` freeze-indicator copy/threshold and the Stats-page explainer string also
reference these (or a small local constant) rather than inlining. Tests assert behaviour via
the constants (e.g. import `STREAK_MILESTONE`) so retuning a value doesn't silently break a
hard-coded expectation.

## Alternatives considered

- **Server push (APNs):** fires even if the app is never opened, but needs APNs certs (USER), device-token storage, and a backend scheduler. Deferred; local notifications deliver most of the value with none of that setup.
- **Premium-only / weekly-grant freeze models:** rejected in favour of the free milestone model (fair for a mostly-free beta, gamified).
