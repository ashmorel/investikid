# Daily Goal + Server Push (M7) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M7 of `docs/2026-06-12-market-leader-roadmap.md`.
Two sub-parts: **7a Daily goal loop** (pure code, ships complete) and **7b server-push
foundation** (backend + JS complete; native entitlement + Firebase project are
operator/Xcode steps, flagged). Push provider decision: **FCM for both platforms**
(one integration; FCM relays APNs for iOS) via the FCM HTTP v1 API with `google-auth` credentials (already a dependency; firebase-admin was rejected — its httpx pin conflicts with the repo's).

## 7a — Daily goal loop

A Duolingo-style daily XP target so every session has a finish line.

**Data** (migration on `user_progress`): `daily_goal_xp` int default 30;
`xp_today` int default 0; `xp_today_date` date nullable. New seam
`app/services/xp_service.py: record_xp(progress, amount, *, today)` — bumps `xp` AND
maintains the `xp_today` day-window (reset when `xp_today_date != today`), returns
`(goal_met_now: bool, goal_was_met_before: bool)` so callers can celebrate exactly once
per day. All three award sites route through it (content `_award_completion`, simulator
`simulator_rewards` ×2).

**API**: `GET /users/me/progress` gains `daily_goal_xp`, `xp_today`, `goal_met`
(computed). `PATCH /users/me/goal {daily_goal_xp}` — allowed values {10, 30, 50}
(kid-pickable: Chill / Steady / Super; 422 otherwise). Parent visibility:
`ChildAnalyticsOut` gains `daily_goal_xp` + `xp_today` (value-only — parents see, don't
set; AADC: goal size is the child's choice).

**Child UI**: StatsCard row 2 becomes the *daily* goal bar (`xp_today / daily_goal_xp`,
"Goal met! ⭐" state with `aria-live` polite announcement; investor tier: no emoji,
"Goal met"); level-XP caption stays in row 3 (the level bar remains in caption form —
the daily ring is the actionable element). Goal size picker in ProfileMenu ("Daily goal:
Chill 10 · Steady 30 · Super 50") via the new PATCH. Lesson-complete screen already
celebrates; goal-met adds one toast line when `goal_met_now` flips (completion response
gains `daily_goal_met: bool`, fired once per day).

## 7b — Server push foundation

**Consent model (COPPA/AADC)**: two gates, both required —
1. Parent master switch per child: `users.push_enabled` bool default False, toggled
   only via parent endpoint `POST /parent/children/{id}/push {enabled}` (mirrors the
   premium/freeze toggle patterns, audited).
2. Device-level OS permission, requested in-app ONLY when the parent switch is on and
   the child taps the existing notifications toggle (no cold prompts).

**Data**: `push_devices` table — id, user_id FK CASCADE, platform ('ios'|'android'),
token (unique), created_at, last_seen_at. Registered via `POST /users/me/push-devices
{platform, token}` (upsert by token; child session), deleted on logout/unregister
(`DELETE /users/me/push-devices/{token}`).

**Send service** `app/services/push_service.py`: `send_to_user(session, user_id, *,
kind, title, body)` via the FCM HTTP v1 API + google-auth (`FIREBASE_SERVICE_ACCOUNT_JSON` env; service is
a no-op with a log line when unconfigured — same pattern as Stripe/Apple guards).
**Frequency cap**: at most 1 push per user per UTC day — stored as
`user_progress.last_push_sent_date` (date, nullable; same migration as 7a's columns).
Invalid-token responses remove the device row.

**v1 trigger** (the one the roadmap names first): **streak-at-risk** — a new step in the
daily cron (`POST /internal/push-streak-risk/run`, CRON_SECRET pattern) finds children
with `streak_count > 0`, `last_activity_date == yesterday`, push_enabled, a registered
device, and no push sent today → "Your {n}-day streak is waiting — one lesson keeps it
alive 🔥" (no emoji for investor tier). Goal-met celebration + weekly-challenge pushes:
deferred (the in-app toast covers goal-met; listed as follow-ups).

**Client**: `src/lib/push.ts` — registers via `@capacitor/push-notifications` ONLY when
native && parent switch on (from `/users/me` gaining `push_enabled`) && child enables the
ProfileMenu toggle; sends token to the backend; unregisters on toggle-off. Web: no-op.
ParentDashboard ChildCard gains the push toggle (next to the existing premium/freeze
controls).

**Operator/Xcode hand-off (before pushes fire on devices)**: create a Firebase project +
upload the APNs auth key; set `FIREBASE_SERVICE_ACCOUNT_JSON` on Railway; `npm i
@capacitor/push-notifications` is done in code but iOS needs the **Push Notifications
capability + entitlements** added in Xcode and a device rebuild; Android needs
`google-services.json`. Until then everything no-ops safely.

## Analytics

`push_sent` joins SERVER_EVENTS (props: surface='streak_risk'); `goal_met` is derivable
from lesson_completed + progress so no new event.

## Testing

7a: xp_service window maths (reset on new day, goal_met_now exactly once, custom goal),
PATCH /goal validation, progress payload, completion response flag, StatsCard goal bar
(both tiers + aria-live + axe), ProfileMenu picker. 7b: device register/upsert/delete,
parent toggle (auth + audit + IDOR), push_service no-op unconfigured + frequency cap +
invalid-token cleanup (firebase mocked), streak-risk cron selection logic (in/out cases),
push_sent event, client lib gating matrix (native/parent/child switch), ChildCard toggle.
Full repo gates.

## Out of scope

Goal-met / weekly-challenge push triggers · quiet-hours windows beyond the 1/day cap ·
web push · notification inbox/history UI.
