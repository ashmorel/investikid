# Outcome-Led Paywall & Mastery Report (M6) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M6 of `docs/2026-06-12-market-leader-roadmap.md`.
**Premise (approved in roadmap):** the paid product's story is *evidence of mastery* —
"your child is mastering real financial skills, here is the proof" — not a feature list.
All data already exists (W3 `level_mastery` + `learning_objectives` + standards; W4 digest
helpers; M4 analytics for measurement). M6 recomposes it. No migration.

## 1. Backend — `GET /parent/mastery-report?days=30`

Parent-authed, sibling of existing /parent routes. Per child of the parent:

```json
{
  "window_days": 30,
  "children": [{
    "user_id": "...", "username": "maya",
    "mastered_count": 3,                     // LevelMastery in window
    "mastered_total": 7,                     // all-time
    "objectives": ["explain what a stock is", "..."],   // flattened from mastered
                                              // levels' learning_objectives (window),
                                              // deduped, capped at 8
    "standards": [{"framework": "...", "code": "..."}], // distinct standards_alignment
                                              // of modules touched in window
    "weak_topic": "budgeting" | null,         // digest's _weak_topic
    "next_recommendation": {"module_title": "...", "lesson_title": "..."} | null
  }],
  "household_mastered_count": 3
}
```

Implementation: extract the digest's mastery-window query into a shared helper
`mastery_report_service.py` (used by both digest and this endpoint) OR reuse via direct
import of digest helpers — prefer a small new `app/services/mastery_report_service.py`
exposing `build_mastery_report(session, parent_email, *, days, now)` that the router
calls; the digest keeps its own (window semantics differ: digest = since-last-digest).
`_weak_topic` and `_next_recommendation` are imported from digest_service (already
module-level functions).

## 2. Parent dashboard — Mastery Report hero

New `MasteryReportCard` at the TOP of ParentDashboard (above the children list):
- Headline per household: "**{N} skills mastered** in the last 30 days" (or the child's
  name when there's exactly one child: "Maya mastered {N} skills this month").
- Per child block: objective chips ("can now: explain what a stock is" …, cap 8 visible),
  standards badge(s) (framework names — same `StandardRef` rendering convention as
  ChildAnalytics), weak-area line ("Worth a look: budgeting — try '{next lesson}'
  together") when present.
- Empty state (no masteries in window): "No new masteries yet — {next lesson} is queued
  up" (keeps the card useful, never shaming).
- Loading skeleton + error fallback per existing dashboard cards; vitest-axe.

## 3. PremiumValueCard — outcome-proof reframe (non-subscribers only, as today)

- Headline becomes evidence-led, fed by the mastery report:
  - With masteries: "**{name} mastered {N} skills this month.** Unlock the full
    curriculum + AI coach to keep the momentum."
  - Without: "Real financial skills, with the evidence to prove it." (generic fallback)
- Below: the benefits list trimmed to 3 (curriculum depth, AI coach, weekly evidence
  email), then the existing pending-request highlight + Subscribe CTA (unchanged
  behaviour, still routes to SubscriptionCard's flow).
- Child-side surfaces unchanged (locks stay gentle — out of scope).

## 4. Weekly digest premium line — copy variants (measured via M4)

- Three variants of the non-subscriber premium line in `email.py`:
  - `a` (current): "{name} just mastered… See your options"
  - `b` outcome-count: "{name} mastered {n} skills this week. Premium unlocks the full
    curriculum + AI coach."
  - `c` evidence: "Want the full picture of what {name} can do with money? Premium adds
    the complete curriculum + AI coach."
- Deterministic assignment: `variant = 'abc'[hash(parent_email) % 3]` (stable per parent,
  no storage). The `digest_sent` analytics event gains `props.variant` (allowlisted key:
  reuse `source`? No — add `variant` to `ALLOWED_PROP_KEYS`). Comparison happens in the
  admin dashboard later via event counts; no new UI in M6.

## Testing

Backend: mastery_report_service (window maths, dedupe/cap, weak topic + recommendation
pass-through, empty household); endpoint auth + shape; digest variant assignment
(deterministic, all three reachable) + `digest_sent` carries variant; `variant` prop
allowlisted. Frontend: MasteryReportCard (counts, chips cap, empty state, single- vs
multi-child headline, axe); PremiumValueCard (evidence headline with data, fallback
without, hidden for subscribers — existing tests updated); ParentDashboard composition.
Full gates per repo convention.

## Out of scope

Child-side lock changes · variant auto-winner logic · digest open tracking ·
Mastery Report PDF/export (post-launch idea).
