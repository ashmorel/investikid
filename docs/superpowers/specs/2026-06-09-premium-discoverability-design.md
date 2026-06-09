# Premium Discoverability (#4) — Design Spec

**Date:** 2026-06-09
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Programme:** Part **#4** of the leveling/premium programme (#1 module UX, #2 leveling+premium model, #3 Level 2/3 pilot — all shipped to `testing`). Triggered by tester feedback that premium isn't obvious. Builds on the now-natural "earned moment" (free Level 2 done → premium Level 3 wall).

## Goal
Surface Premium **proactively** (not only when a child hits a wall), across four gentle, dismissible, frequency-capped surfaces. Kids only ever **ask**; parents decide and pay. No dark patterns aimed at children.

## Principles (kids' app)
Value-led copy (what Premium *gives*), never pressuring; every child-facing nudge is **dismissible** and **frequency-capped**; no purchase UI is ever shown to a child; WCAG 2.2 AA. The existing per-day request dedupe (4B) already prevents spamming the parent.

## Current state (verified)
- `premiumApi.requestUnlock({kind, label})` (`frontend/src/api/premium.ts`) → `POST /premium/request`; `PremiumRequestKind = 'module'|'level'|'challenge'|'ticker'|'coach'`. Backend `premium.py` stores `context_kind` as a free string (`Field(min_length=1, max_length=20)`) → a new `'home'` kind works without backend change. Per-day dedupe + a `declined` state exist; `PremiumPaywall` returns `sent`/`already`/`declined`.
- Copy/config: `frontend/src/lib/premiumConfig.ts` — `PREMIUM_BENEFITS` (4 items), `PAYWALL_TITLE`, `PAYWALL_CTA`, `PAYWALL_REQUEST_DECLINED`. `PremiumBadge` exists (`components/child/PremiumBadge.tsx`).
- `Home.tsx` (child): hero, stats, level progress, portfolio snapshot, review banner, achievements, module tiles — **no premium surface**. `me` (`authApi.me`) carries `is_premium` (via the `['me']` query already used).
- `Module.tsx` (post-#1): renders level cards; shows a "Module complete → Next" CTA when all levels complete. `LevelOut` has `state`, `locked_reason: 'premium'|'progression'|null`, `is_premium`. `LevelCard` already routes premium-locked taps to the paywall.
- Parent dashboard + `SubscriptionCard` + a pending premium-requests card exist (4B). `GET /parent/premium-requests` returns pending requests with `child_username` + `context_kind`/`context_label`.

---

## Section A — Child Home upsell card
**Create** `frontend/src/components/child/PremiumUpsellCard.tsx` + a tiny `frontend/src/lib/premiumNudge.ts` helper.
- `premiumNudge.ts`: `isDismissed(key: string): boolean` / `dismiss(key: string): void` backed by `localStorage`, with a **7-day** re-appear (store an ISO timestamp; dismissed if `< 7 days` ago). Guard against unavailable `localStorage` (try/catch → treat as not-dismissed). Pure, unit-testable.
- `PremiumUpsellCard`: renders only when `!me.is_premium` **and** `!isDismissed('home-upsell')`. Brand card: 🌟 + `PAYWALL_TITLE`, two `PREMIUM_BENEFITS`, an **"Ask my grown-up"** button (`requestUnlock({kind:'home', label:'Premium'})`) reusing the paywall's sent/already/declined copy, and a dismiss `×` (`aria-label="Dismiss"`) → `dismiss('home-upsell')` + hide. ≥44px targets, semantic brand tokens.
- **Wire into `Home.tsx`**: render `<PremiumUpsellCard />` for non-premium children (e.g. below `LevelProgressCard`). Premium children never see it.

## Section B — "Earned moment" nudge (Module page)
**Modify** `Module.tsx` (+ optionally a small `PremiumLevelNudge` piece).
- Compute the "next locked level": the first level whose `state === 'locked'`. If it's `locked_reason === 'premium'` **and** all earlier (free) levels are `completed`, the child has *earned* their way to the wall.
- When that holds, render a celebratory nudge **in place of** the #1 "Module complete → Next module" CTA: "🎉 You're ready for {nextLevel.title}! Unlock Premium to keep going 🌟" + **"Ask my grown-up"** (`requestUnlock({kind:'level', label: nextLevel.title})`) + dismiss. Once-per-module cap via `premiumNudge` key `level-nudge:{moduleId}`.
- If the next step is **not** premium-locked, the existing #1 CTA is unchanged.

## Section C — Parent-side value + subscribe CTA
**Modify** the parent dashboard.
- Add a concise **"Premium gives your child:"** block (the `PREMIUM_BENEFITS`) + a prominent **Subscribe** CTA, placed near the pending premium-requests card (reuse/position `SubscriptionCard`).
- When `GET /parent/premium-requests` returns pending item(s), highlight contextually: e.g. "{child_username} asked to unlock Premium — subscribe to say yes." (Only for non-subscribed parents; subscribed parents see normal subscription management.)

## Section D — Locked-cue polish
**Modify** the module-tile and level-card render paths.
- Show a consistent **"⭐ Premium"** badge (reuse `PremiumBadge`) on premium-locked **module tiles** (Home + Lessons module list) and **level cards** (premium-locked levels), plus a one-line teaser ("Unlock to continue"). Today only a lock icon shows. Tapping still opens the paywall (unchanged).

---

## Backend
**None new.** `requestUnlock` already accepts `kind:'home'` (free-string `context_kind`). Only widen the FE type: `PremiumRequestKind = '... | 'home'`. No DB migration. (If a future audit wants `kind` constrained, that's out of scope here.)

## Testing (vitest + vitest-axe; no backend tests needed)
- `premiumNudge.test.ts`: dismiss persists; re-appears after 7 days; missing/throwing `localStorage` → treated as not-dismissed.
- `PremiumUpsellCard.test.tsx`: renders for non-premium + not-dismissed; **hidden** for premium; hidden when dismissed; "Ask my grown-up" calls `requestUnlock({kind:'home',...})` and shows the sent state; dismiss persists; axe-clean.
- `Module.test`/`child-Module.test`: when next level is premium-locked + earlier free levels complete → earned-moment nudge with "Ask my grown-up" (not the plain next-module CTA); when next step is non-premium → existing CTA unchanged; nudge dismiss capped per module.
- Parent dashboard test: value block + Subscribe CTA render for non-subscribed parent; pending request highlighted; subscribed parent doesn't see the upsell.
- Locked-cue test: premium-locked module tile + level card show the "⭐ Premium" badge; free ones don't.

## Verification
Frontend: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. No backend change, no migration, no `cap sync`. Work on `testing`; do NOT promote.

## Out of scope
Pricing/plan changes; new billing flows; constraining the backend `kind` enum; email/push premium marketing; any change to the gate logic (#2) or the request/dedupe backend (4B); A/B testing.
