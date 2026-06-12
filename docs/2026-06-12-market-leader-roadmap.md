# InvestiKid — Market-Leader Roadmap (v2)

**Date:** 2026-06-12
**Owner:** Lee Ashmore
**Status:** Active — supersedes `docs/2026-06-10-best-in-class-roadmap.md` (W1–W7, all DONE) as the tracking index.
**Trigger:** Updated external product review (8.2/10 beta, up from 7/10). Goal: move into the 8.7–9.0 band as a **revenue-generating, sticky, market-leading** children's investment-education app, via TestFlight beta to a public paid App Store launch in ~12 weeks.

---

## Strategic position (unchanged, now validated)

The review confirms the lane: **not a kids' bank** — the financial-education and investing-confidence app. We win on depth of education, the investing simulator, safe AI coaching, regional curriculum, and **parent-visible outcomes**. The paid product is **evidence of mastery for parents** — "your child is mastering real financial skills, and here is the proof" — not "unlock more content."

## Reality check (what the 8.2 review could not see)

The commercial plumbing is further along than both the review and the 2026-06-05 backlog imply. Already built in this repo:

- **Billing stack**: Stripe checkout + customer portal + webhook (single monthly price, 7-day first-subscription trial), Apple StoreKit verification, Google Play billing, trial-ending reminder email, premium-clarity paywall + premium-discoverability passes (specs 2026-06-06 → 06-09).
- **Premium content depth**: Level 2 (free) + Level 3 (premium) rolled out across **all** modules (commit `4dbfb10`), on top of the 3 seeded premium modules and 3 teen modules.
- **Outcome machinery**: level mastery records, verbatim MaPS/Jump$tart standards alignment, 105+ learning objectives, weekly parent digest with per-module conversation prompts (W3/W4).
- **Compliance**: parent self- and child-account deletion (Apple 5.1.1(v)) on `testing`; COPPA/AADC spine throughout.

The genuine gaps are therefore **not plumbing**. They are: shipping what's parked on `testing`/`staging`, Home-screen focus, subscription *packaging*, daily-habit stickiness mechanics, teen validation with real users, measurement, and launch operations. That is what this roadmap covers.

## KPIs (define now, measure from Phase 1)

Targets are starting hypotheses (kids-edtech benchmarks), revised once real data flows. They require M4 (analytics) — today there is **no product analytics** beyond server logs.

| KPI | Target | Why |
|---|---|---|
| Activation | ≥60% of new child accounts complete a first lesson within 24h | Funnel health; `/try` + Home hero feed this |
| D7 / D30 child retention | ≥25% / ≥12% | Stickiness engine's success measure |
| Trial start rate | ≥15% of active families within 30 days of signup | Paywall/packaging effectiveness |
| Trial → paid conversion | ≥40% | Industry-strong for a 7-day trial; outcome-led story is the lever |
| Weekly digest open rate | ≥45% | The digest is the retention + conversion engine for parents |
| Crash-free sessions | ≥99.5% | The review's "proving reliability" point, quantified |

---

## Phases & workstreams

### Phase 0 — Ship the shelf (Week 1)

**M1 · Promotion train to production.** Everything W2–W7 plus account deletion is parked value until it reaches users. Promote `testing` → `staging` → `main` per the runbook: **production DB snapshot ask first** (standing rule — W3/W4/W5 carry migrations) and a **committed device-QA PASS sign-off** on real iPhone + Android. Includes the W4 digest cron step and setting `YOUTUBE_API_KEY` so video health checks go live.
**Success:** prod runs the full W2–W7 feature set; digest emails flowing; `/try` public.

**M2 · TestFlight beta cohort + ops hygiene.** Distribute the TestFlight build (build 3 exists) to a recruited cohort of 10–20 real families (aim for a spread: 8–10, 11–13, and 15–18-year-olds — the last group feeds M10). Ops debt from the backlog: rotate `CRON_SECRET`, document R2 public-by-URL decision, enforce R2 upload size server-side, decide on the OpenAI premium-quota top-up, instrument real Coach/moderation token counts to confirm the ~95% gross-margin model.
**Success:** ≥10 families active on TestFlight; cost model confirmed with real token data.

### Phase 1 — One thing to do next (Weeks 1–3)

**M3 · Home hierarchy redesign. ✅ BUILD DONE (2026-06-12, on `testing`).** Figma exploration ("M3 — Home Hierarchy Exploration" page, file `h5xrUTiNDZqqhu4pvYprqc`) → owner picked Variant A hierarchy + B's combined stats card + C as investor skin → spec/plan (`docs/superpowers/{specs,plans}/2026-06-12-home-hierarchy-redesign*`) → TDD build. Home now: hero (one primary action) → combined `StatsCard` → `QuickLinksRow` chips → slim premium row → browse-all; modules grid removed; investor tier renders flat/no-Penny/no-emoji via new `tierConfig` knobs. Deleted StatsBar/LevelProgressCard/PortfolioSnapshotCard/ReviewBanner/AchievementsStrip. FE suite 903 green incl. both-tier axe. Pending: device QA at next promotion; M4 must instrument hero-CTA + chip taps on day one. Original scope: The review's sharpest UX critique: Home has next-lesson, stats, level progress, premium, portfolio, review, badges, and modules competing. **Step 1 is Figma variant exploration**: generate 2–3 Home hierarchy variants (hero-dominant, collapsed-tiers, teen-density) from the existing design-system tokens file (see `docs/figma-handoff.md`), pick one, *then* spec and build. Redesign around **one primary action** — a dominant "Continue" hero (the next-lesson resolver is already the strongest asset) — with everything else demoted to clearly secondary tiers (collapsed, smaller, or moved to Stats/Profile). Apply `tierConfig` density so the Investor-Mode variant reads even cleaner. Run vitest-axe on the new layout.
**Success:** a child landing on Home can state the one thing to do next; primary-CTA tap-through measurable via M4 (target: most Home sessions start the next lesson).

**M4 · Privacy-safe product analytics. ✅ BUILD DONE (2026-06-12, on `testing`).** Spec/plan `docs/superpowers/{specs,plans}/2026-06-12-product-analytics*`. Shipped: `analytics_events` table (migration `a8b9c0d1e2f3`) + `product_analytics_service.record()` seam; server hooks (lesson_completed, subscription_activated, trial_started [Stripe], digest_sent); batched authenticated ingest for 4 client events (home_view, home_cta_tap, quicklink_tap, paywall_view — M3's success metric now measured); 13-month raw-event retention via daily cron + account-purge detach + privacy-notice paragraph + import-surface invariant test; `GET /admin/analytics/summary` (activation, weekly D7/D30 cohorts, trial funnel, engagement) + /admin Analytics dashboard with 7/30/90d picker. Out of v1 (footnoted in dashboard): /try tracking, digest opens (Resend), crash-free, Apple/Google trials. Original scope: First-party event capture (backend table + lightweight client events: activation, lesson completion, Home CTA taps, paywall views, trial starts, digest opens) with admin funnel/retention dashboards. **No third-party trackers on child surfaces** (COPPA/AADC); counts and funnels, not behavioural profiles; respect the existing `profiling_enabled` AADC gate; retention-purge integration.
**Success:** the KPI table above is a live admin dashboard, not a guess.

### Phase 2 — Parents pay for outcomes (Weeks 2–5)

**M5 · Pricing & packaging. ✅ BUILD DONE (2026-06-12, on `testing`) — operator dashboard steps pending.** Spec/plan `docs/superpowers/{specs,plans}/2026-06-12-pricing-packaging*`. Decision: **family SKU dropped** — entitlement is already household-wide, so "one subscription covers all your children" is the headline instead. Shipped: plan catalog (annual $39.99/£29.99/HK$298 lead w/ Save 33%, monthly $4.99/£3.99/HK$38), plan-aware Stripe checkout (annual default, graceful fallback), `GET /billing/plans` (household display currency), Apple/Google verify accept monthly+annual product set, SubscriptionCard radiogroup plan picker (web + native, dynamic IAP product ids). ⏳ OPERATOR (per spec hand-off): create Stripe monthly+annual Prices w/ GBP/HKD currency options + env vars; App Store Connect `premium_annual` + price points + **Small Business Program enrolment**; Play Console `premium_annual`; set `*_ANNUAL` env vars. Original scope: Implement the decided structure: **lead with annual $39.99/yr**, monthly $4.99/mo, family plan (~$59.99/yr, up to 4 children), regional price tiers (UK £3.99/£29.99, HK ~HK$38 — App Store Connect price points, not FX). Work: Stripe multi-price products + plan picker (today: single `stripe_price_id`), matching Apple/Google IAP products, family-plan entitlement fan-out across a parent's children, **Apple Small Business Program enrolment** (15% vs 30%).
**Success:** a parent can choose monthly/annual/family on web and iOS at regional prices; annual is the visually-default choice.

**M6 · Outcome-led paywall & Mastery Report. ✅ BUILD DONE (2026-06-12, on `testing`).** Spec/plan `docs/superpowers/{specs,plans}/2026-06-12-outcome-paywall-mastery-report*`. Shipped: `GET /parent/mastery-report` (per-child window masteries, deduped objectives capped 8, standards, weak topic, next recommendation); `MasteryReportCard` hero at the top of the parent dashboard ("Maya mastered N skills this month" + "can now:" objective chips + standards line + weak-area guidance, encouraging empty state); `PremiumValueCard` reframed evidence-first (real mastery counts in the headline, benefits trimmed to 3); weekly-digest premium line now has 3 copy variants (deterministic per parent email, tagged on the `digest_sent` analytics event for comparison via M4). Child-side locks untouched. Original scope: Reframe every premium surface around evidence: parent dashboard gets a **Mastery Report** hero (mastered objectives with dates, standards badges, weak-area guidance — all W3 data, recomposed); `SubscriptionCard`/`PremiumValueCard` copy moves from feature-list to outcome-proof ("Maya mastered 12 skills this month — unlock the full curriculum + AI coach"); the weekly digest's premium line gets 2–3 copy variants measured via M4. Child-side premium locks stay gentle (already the case).
**Success:** the subscription story *is* the parent report; trial-start rate measurable against the ≥15% target.

### Phase 3 — Stickiness engine (Weeks 4–8)

**M7 · Daily goal + server push. ✅ BUILD DONE (2026-06-12, on `testing`) — Firebase/Xcode operator steps pending.** Spec/plan `docs/superpowers/{specs,plans}/2026-06-12-daily-goal-push*`. 7a: daily XP goal (Chill 10/Steady 30/Super 50, kid-picked in ProfileMenu, default 30) — `record_xp` seam across all 3 award sites, goal bar in StatsCard (aria-live "Goal met!"), once-per-day celebration on lesson completion, parent-visible in ChildAnalytics. 7b: push foundation — `push_devices` registry, double-gated consent (parent master switch `users.push_enabled` via dashboard toggle + child in-app toggle, server-enforced 403), FCM `push_service` (safe no-op until configured, 1 push/child/day, dead-token pruning), streak-at-risk daily cron trigger (tier-aware copy), `push_sent` analytics event. Migration `b9c0d1e2f3a4`. ⏳ OPERATOR before pushes fire: Firebase project + APNs key upload, `FIREBASE_SERVICE_ACCOUNT_JSON` on Railway, **Xcode: Push Notifications capability + rebuild** (new @capacitor/push-notifications plugin synced), Android `google-services.json`. Original scope: A Duolingo-style **daily goal** (small XP target, parent-visible, kid-pickable size) giving every session a finish line, layered on existing streaks/freezes. Add **server push notifications** (today only an opt-in local streak reminder exists): streak-at-risk, new weekly challenge, goal-met celebration — parent-consented, off by default, frequency-capped, AADC-compliant.
**Success:** push opt-in offered at the right moments; D7 retention movement attributable in M4 dashboards.

**M8 · Close the spend loop (Penny economy). ✅ BUILD DONE (2026-06-12, on `testing`).** Spec/plan `docs/superpowers/{specs,plans}/2026-06-12-penny-cosmetics*`. Learning-coins economy: 1 coin per XP via the `record_xp` seam (deliberately NOT simulator cash — that would corrupt the investing-lab metric), retroactive backfill `virtual_coins = xp` (migration `c0d1e2f3a4b5`). 8-item accessory catalog (2 premium-exclusive ✨ — coins are never purchasable), shop API with coin/premium/duplicate guards (race-safe SAVEPOINT), one-equipped-at-a-time. Penny renders the equipped accessory everywhere via an SVG emoji overlay; `/shop` page (confirm-before-spend, paywall hook on premium items) + ProfileMenu entry with coin balance. Original scope: Virtual cash currently accumulates with nothing to buy (the deferred earn→spend scope). Add a small **cosmetics store**: Penny accessories/outfits and app themes purchasable with earned virtual cash — including a few Investor-Mode-appropriate (non-childish) themes. Play-money only; zero real-money or entitlement crossover.
**Success:** earned cash has a use; cosmetic ownership visible on Home/profile.

**M9 · Weekly group challenges + seasonal events.** On top of parent-mediated leaderboard groups: a weekly co-op group challenge ("group completes 20 lessons") and an admin-authorable seasonal event frame (themed week + bonus XP + special badge). Same COPPA spine — no child-initiated social, no messaging.
**Success:** groups have a reason to exist weekly; events runnable from /admin without a deploy.

### Phase 4 — Teen validation (Weeks 5–9)

**M10 · Structured 15–18 testing → Investor Mode iteration.** The review's #1 priority and the cheapest de-risk: 5–8 real 15–18-year-olds from the M2 cohort, structured script (tone, mascot presence, density, simulator credibility, "would you open this at school?"). **Prepare Figma visual-direction mockups for the sessions** (darker/flatter theme, dialled-back mascot, denser simulator) so testers react to candidate directions *before* any code is committed; then one iteration pass on Investor Mode's visual maturity from the findings.
**Success:** documented findings + one shipped iteration; teens describe it as "an investing app for me," not "a kids' app with a teen skin."

### Phase 5 — Public launch (Weeks 9–12)

**M11 · Store presence.** Finalise the **"Penny in a sprouting coin"** icon (backlog pick) at icon resolutions; App Store listing + screenshots framed on the parent-outcome story; ASO keyword pass; privacy nutrition labels (include the YouTube/Google-processor disclosure); 9+/12+ age rating confirmed.
**Success:** listing assets done and reviewed; app passes App Store review.

**M12 · Launch readiness.** Full device-QA sign-off on the launch build (the standing gate — billing, video, auth, progress-save, offline on real hardware); observability check (alert recipients, video-health cron, LLM-failure alerts); support flow (support email + in-app feedback triage routine); load sanity on Railway; prod backup cadence confirmed.
**Success:** launch-week checklist green; public launch with billing live.

---

## Post-launch bets (sketched, not committed)

- **School/teacher packaging** — the standards-alignment + mastery records + group machinery make a classroom offer credible (teacher dashboard, class groups, B2B licensing — the highest-margin hedge against free competitors). First step: 2–3 teacher conversations during beta, zero code.
- **Android / Play Store launch** — Google Play billing is already built; needs the device-QA matrix + listing.
- **Regional curriculum depth** — more `country_codes`-localised content (AU/CA next), reinforcing the moat Zogo-style apps lack.
- **AI Coach proactivity** — weekly personalised "your plan this week" from the recommendations engine, premium-gated.

## Risks

| Risk | Mitigation |
|---|---|
| App Store review friction (kids + finance + IAP) | Education positioning, 9+/12+ rating, IAP correctness in M5, deletion compliance already shipped |
| Home redesign becomes another layer of clutter | M3 has a hard rule: one primary action; everything else must justify its tier |
| Solo-operator QA discipline slips | Keep the procedural sign-off gate non-negotiable (review's point: trust is earned per release) |
| LLM cost/quota at scale | M2 token instrumentation; premium→standard fallback already ships |
| Charging during beta hurts word-of-mouth | Beta cohort gets generous comped premium; billing tested with sandbox/TestFlight purchases |
| 7% projection misread as a promise | Keep reinforcing variance/loss framing wherever projections appear (review flag; audit copy in M6) |

## Sequence & dependencies

M1 → M2 unlock everything (parked value + real users + real data). M4 (analytics) should land early because M3, M6, M7 and M10 are all measured through it. M5/M6 before M7–M9: the conversion story must be in place while stickiness work compounds it. M10 runs alongside (cohort recruited in M2). M11/M12 close.

```
Wk:  1  2  3  4  5  6  7  8  9  10 11 12
M1   ██
M2   █████
M3   ████████
M4   ████████
M5      ███████████
M6         ████████
M7            ████████
M8               ████████
M9                  ████████
M10              █████████████
M11                        ████████
M12                              ███████
```

## Out of scope (unchanged)

Card/allowance/chore/banking utility; App Store Kids Category (we target 9+/12+); re-hosting third-party video. R2 self-hosting stays parked.

## Tracking

Each M-workstream graduates via the superpowers pipeline: brainstorm → design spec (`docs/superpowers/specs/`) → implementation plan (`docs/superpowers/plans/`) → TDD on `testing` → gated promotion. M1/M2/M10/M11 are operational (runbooks/checklists, little or no code). This doc is the index — update statuses as workstreams ship.
