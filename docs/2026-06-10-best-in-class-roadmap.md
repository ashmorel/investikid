# InvestiKid — Best-in-Class Roadmap

**Date:** 2026-06-10
**Owner:** Lee Ashmore
**Status:** Active — tracking doc for the goal "make InvestiKid best-in-class for childhood investment education"
**Trigger:** External product review (7/10 beta). This roadmap responds to that review, grounded in the actual `ashmorel/investikid` codebase (not assumptions).

## Strategic position (the lane we win)
InvestiKid is **"Duolingo for financial literacy" + an investing simulator + a safe AI tutor + parent insight + regional curriculum.** We do **not** chase card/allowance/chore banking utility — that's Greenlight/GoHenry/Step's lane and carries heavy KYC/regulatory weight. We win on **depth of education, investing confidence, and parent-visible outcomes.** Strongest today for ages 10-14; the work below extends credibility to 15-18.

## Reality-check (what the black-box review underrated)
The codebase is further along than an external review could see:
- **Age tiers already exist** — `age_tier.py` (boundary 14: "explorer" 10-13 vs "investor" 14-18) drives Coach register, hero copy, module order. Gap = make it *visible and mature*, not build it.
- **Simulator already resists churn** — XP capped 5/trade, 25/day (`simulator_rewards_config.py`); missions reward diversify/invest-amount; no urgency mechanics. Gap = *surface* long-term signals.
- **Parent analytics already compute per-module/level mastery** (`analytics_service.py`). Gap = *push* it as a weekly outcome story.
- **Video is ~80% hardened** — `youtube-nocookie`, an iOS `/yt.html` proxy that fixes WKWebView error-153, `playsinline`/`rel=0`/`modestbranding`, transcript fallback, and a daily `video-health` cron all exist. Gaps are narrow (see W2).

## Video strategy (decided)
- **Curriculum video stays entirely curated-from-YouTube** (embedded, not re-hosted — re-hosting others' videos isn't legal).
- **Target App Store rating: standard 9+/12+** (not the Kids Category) → embedded YouTube is shippable.
- **Cloudflare R2 self-hosting is parked** (code is wired; flip-the-switch later only if we add premium/branded/ad-free core video or ever move to the Kids Category).
- **Must-do disclosures (COPPA/UK Children's Code still apply):** keep `youtube-nocookie`; disclose the YouTube embed + Google as a processor in the privacy policy.

---

## Workstreams (6, across 4 phases)

### Phase 0 — Trust floor (release-critical, do first)
**W1 · Physical-device QA gate. ✅ DONE (2026-06-10).** Procedural gate shipped: `docs/release-qa-checklist.md` (15-row device matrix), `docs/release-signoffs/` (per-release sign-off log + README), and a new **hard-gate step in the production-promotion runbook** (`docs/deployment-environments.md`) — no promotion to `main` without a committed PASS sign-off run on a real iPhone + Android. Enforcement is procedural (matches the manual merge-based promotion). **Success met:** the matrix + sign-off requirement now block release.

**W2 · Video reliability & kid-safety (narrowed — most already built). ✅ DONE (2026-06-10, on `testing`, CI green).** Embeddability-aware health check (`blocked` status), admin alert + badge, IFrame-API end-screen → app UI, graceful failure, privacy disclosure. Dormant until `YOUTUBE_API_KEY` is set; awaiting prod promotion + a native rebuild for the IFrame change to reach devices. Real remaining gaps: (a) the health cron's **oembed check returns 200 for embedding-disabled videos**, so it can't catch the 153 failure mode — add embeddability detection; (b) **no IFrame-API end-screen control** → YouTube's related-video end-screen still shows (kid-safety); (c) **graceful in-app fallback** only fires on a malformed ID, not on an iframe load failure; (d) **privacy-policy disclosure**; (e) verify build 2 (with baked `VITE_WEB_ORIGIN`) actually clears the device-153 the tester saw. Detailed spec: `docs/superpowers/specs/2026-06-10-video-reliability-design.md`. **Success:** curated YouTube plays reliably on device, the end of a video lands on our "next lesson" UI (not YouTube recommendations), and the cron flags un-embeddable videos before a child hits them.

### Phase 1 — The willingness-to-pay unlock
**W3 · Curriculum credibility. ✅ DONE (2026-06-11, on `testing`, CI green).** W3a: schema (`standards_alignment`/`sources`/`learning_objectives` + `level_mastery` table with backfill migration), mastery recorded immutably on the existing pass semantics, exposed via child/parent/admin APIs. W3b: verified content pack seeded — verbatim MaPS/YE + CEE/Jump$tart 2021 mappings, official sources, 105+ objectives (adversarially checked vs lessons, zero overclaims). W3c: child "you'll learn" block + Mastered ✓ stamp, parent standards badge + mastery dates, admin editors. Awaiting prod promotion (includes a DB migration → snapshot + device-QA gates apply).

**W3 (original scope).** Today: `pass_threshold` + `TopicMastery` exist; **no** learning-objective / sources / standards fields. Change: add `learning_objectives`, `sources`, `standards_alignment` to Module/Level/Lesson; map modules to recognised frameworks (UK: Money & Pensions Service "My Money" framework; US: FDIC Money Smart / Jump$tart); add an explicit **end-of-level mastery attestation** (not just a score). Surface objectives + a standards badge in-app. **Success:** every module shows objectives + standards badge; mastery is an auditable record.

**W4 · Parent outcome reports. ✅ DONE (2026-06-11, on `testing`, CI green).** Weekly outcome email per parent: masteries rendered through W3 objectives ("can now…"), lessons/streak, weak topic (gap detection), next lesson (recommendations), authored conversation prompt per module, outcome-led premium line for non-subscribers. Default-on with a "Weekly progress email" toggle in parent preferences; quiet weeks skipped silently; daily cron + 7-day per-parent gate (`/internal/weekly-digest/run`). ⚠️ Cron step rides to `main` only via promotion (4C gotcha). Includes a DB migration → snapshot + device-QA gates apply at promotion.

**W4 (original scope).** Today: rich per-child analytics in-dashboard; **no email digest** (only `trial_ending`; Resend wired). Change: a scheduled **weekly parent digest** (in-app + email) — skills mastered, weak areas, recommended next lesson, and a concrete "talk to your child about…" prompt. Re-point premium's strongest, **outcome-based** message into the parent area; keep child prompts gentle (already the case). **Success:** parents get a weekly "here's what they learned" email; premium copy is outcome- not badge-led.

### Phase 2 — Win 15-18
**W5 · Visible teen "Investor Mode." ✅ DONE (2026-06-11, on `testing`, CI green).** W5a: visible "Investor" chip, subtle no-emoji celebrations, compact density (all `tierConfig` knobs), per-child parent override (Auto/Explorer/Investor; new `users.tier_override` migration). W5b: three 14+ modules seeded — Student Money: University & Beyond, Investing for the Long Term, Your Brain on Money (63 lessons, full credibility envelope, maths verified) — plus **real age gating**: `min_age`/`max_age` now enforced in browse, direct access, next-lesson, and parent analytics paths (was recommendations-only; gates on actual DOB age, never the tier override).

**W5 (original scope).** Today: tier logic exists but is silent. Change: a visible, mature 14-18 skin (cleaner UI, dialled-back mascot, "investor" tone) + content expansion: student finance/university, credit & debt, ISAs/Junior ISAs / 401k-style wrappers, side hustles, long-term investing & compounding (reuse the `extra_levels` seed pattern + tier gates). **Success:** a 16-year-old's app reads like a teen investing lab.

### Phase 3 — Simulator depth
**W6 · Long-term behaviour surfacing. ✅ DONE (2026-06-11, on `testing`, CI green).** Real 1% trade commission (charged on buys+sells, admin-configurable 0–10%, AppSetting — no migration; fee itemised in TradeForm + response + `GET /market/trade-config`); sell-at-loss reflection step (three reasons, teach-then-proceed, never blocks); DiversificationCard (5-step spread meter from holdings); GrowthProjectionCard (10/20/30y at 7%, "illustration not a promise"). The per-stock Time Machine remains the backward-looking compounding view.

**W6 (original scope).** Today: anti-churn rewards exist but diversification/fees/reflection/compounding aren't shown. Change: a **diversification meter** (distinct tickers already tracked), a **"why are you selling?" reflection** before a sell, light **fee/spread modelling** as a teaching moment, a **compounding-over-time visualiser**. **Success:** the simulator visibly rewards patience, research, and diversification.

### Phase 4 — Funnel
**W7 · Demo / no-account mode.** Today: **none** — signup+consent gate everything. Change: one polished module + a simulator taste with no account, converting to signup at the value moment. **Success:** a parent or teen can try a full lesson before creating an account.

---

## Sequence
P0 (W1→W2) → P1 (W3→W4) → P2 (W5) → P3 (W6) → P4 (W7). Reliability/video = trust floor; credibility + parent outcomes = monetization unlock; teen mode = differentiation; simulator depth + demo = deepen/widen the funnel. Maps directly to the review's four score-drivers (reliability, video, age-tiering, parent-visible outcomes), in priority order.

## Explicitly out of scope
Card/allowance/chore/banking utility (different lane, heavy regulation); App Store Kids Category (we target 9+/12+); re-hosting third-party YouTube content (not legal). R2 self-hosting parked, not deleted.

## Tracking
Each workstream graduates via the superpowers pipeline: brainstorm → design spec (`docs/superpowers/specs/`) → implementation plan (`docs/superpowers/plans/`) → TDD build on `testing` → gated promotion. This doc is the index; update statuses as workstreams ship.
