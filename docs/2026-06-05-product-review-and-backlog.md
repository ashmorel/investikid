# InvestiKid — Product Review & Follow-up Backlog (2026-06-05)

> Findings from a 5-part owner review (flow/engagement, security/PII, premium content,
> pricing, app icon). Captured for follow-up. Nothing here is implemented yet — each
> thread should go through brainstorm → spec → plan before building.
> Source of truth for programme status stays `docs/superpowers/PROGRESS.md`.

---

## 1. Logical flow & engagement (ages 10–18)

**Verdict:** IA is sound; engagement foundation is strong but thin on retention hooks.

### Flow strengths
- Clean IA: Home · Quests · Progress · Simulator · Stats; consistent Quests → Module → Level → Lesson.
- Back button on every deep screen; good post-lesson loop (confetti → XP/streak chips → auto-advance).
- Next-lesson resolver gives a returning kid one obvious "Continue" CTA (strongest asset).

### Flow snags to fix — ✅ DONE 2026-06-05 (commits `49e10f4`→`f18c973`, pushed to main)
- [x] **Two competing "what's next" surfaces on Home** — the grid's highlighted tile now derives from `useNextLesson().moduleId` (same resolver as the hero), so they can't disagree. `useRecommendations` retained only for the review banner.
- [x] **Vocabulary drift** — locked literal **Module → Level → Lesson** everywhere a child reads (nav tab → "Learn", headings/counts/lesson-chrome/coach/hero-greeting copy all swept; `tests/unit` mirror updated). Grep-verified no user-facing "quest" strings remain.
- [x] **Theme break on Progress screen** — `StrengthsGaps.tsx` re-skinned to the light semantic tokens; status text bumped to `success-700`/`accent-700` and ring fill darkened to `#7c3aed` to keep **WCAG 2.2 AA** on the white surface.
- [ ] **Locked premium = soft dead-end** — deferred to item 4 (pricing/paywall), as planned.
- [x] Minor: `TopNav` monogram "IE" → "IK".
- Spec/plan: `docs/superpowers/{specs,plans}/2026-06-05-flow-cleanup*`. Full FE suite green (577), build OK, `cap sync ios` done (iOS device view needs a USER Xcode rebuild — copy/colour only, no native change).

### Engagement gaps + top 5 priorities
Foundation present: XP, levels, streaks, badges, weekly challenges, leaderboard, Penny mascot, varied lesson formats, Simulator differentiator.

1. [x] **Re-engagement layer (3A)** — ✅ DONE 2026-06-05 (commits `4e04975`→`cd4c6e4`, pushed). Streak-freeze (earn 1 per 7-day milestone, cap 2, absorbs a single missed day; `streak_config.py` tunables + `streak_freezes` on `UserProgress`, migration `a1b2c3d4e5f7`) + 🛡️ indicator in `StatsBar`. Opt-in on-device **local** notification (Capacitor `LocalNotifications`): "Daily streak reminder" toggle in `ProfileMenu` (off by default, native-only, no auto-prompt), evening streak-at-risk nudge, cancelled once you practice. Server **push** + "new challenges" nudge deferred. Spec/plan `docs/superpowers/{specs,plans}/2026-06-05-reengagement-streak-defense*`. BE 624 / FE 590 green; iOS plugin synced (`Package.swift`) — needs a USER Xcode rebuild to verify on device.
2. [ ] **Social done right** — friends/class leaderboards + challenges via invite/class-code, replacing the demotivating global anonymous board.
3. [ ] **Age-tier mode (10–13 "Explorer" vs 14–18 "Investor")** — derived from DOB already collected; flips copy tone, mascot prominence, default module order, Simulator emphasis. Resolves the core 10-vs-18 tension without building two apps.
4. [ ] **Unify flow** — one vocabulary, one Home "next action", re-skin Progress.
5. [ ] **Close earn→spend loop + wire in Simulator** — let XP/levels unlock tangibles (Penny customization, simulator cash, themes); award XP/challenge progress for simulator activity; add lesson→simulator handoffs.

### Age-range note
Tone/visuals skew ~10–13; content (stocks, crypto, taxes, multi-currency sim) skews older. Same kid gets a mismatched wrapper either way. The age-tier mode (#3) is the fix.

---

## 2. Security & PII

**Verdict:** No personal data leaks through the API. No Critical issues. One real bug to fix before beta.

### Fix before beta (High)
- [x] **Parent logout doesn't clear the session in prod + parent sessions are non-revocable for 7 days.** ✅ DONE 2026-06-05 (commits `af0a454`→`eaf670b`, pushed to main).
  - Added a DB-backed `ParentSession` (`jti` + `revoked_at`) mirroring child `RefreshToken`; `issue_parent_session` persists a row, `decode_parent_session` returns `(email, jti)`, new `revoke_parent_session`.
  - `get_current_parent` now 401s on missing/revoked/expired `jti`; `logout` revokes the row AND clears the cookie with matching `samesite`/`secure`/`httponly`/`path`.
  - Migration `f0a1b2c3d4e5`. Spec + plan in `docs/superpowers/{specs,plans}/2026-06-05-parent-session-revocation*`. One-time effect: parents signed in pre-deploy must log in once.

### Cheap hardening (schedule, not blockers)
- [ ] Document that **hosted premium videos are public-by-URL** (gating stops handout, but the file streams to anyone with the link) — record as a deliberate decision in the R2 setup guide.
- [ ] **Enforce R2 upload size on the object** (content-length-range / bucket limit), not just client-declared `size_bytes`.
- [ ] Prefer **POST/fragment over `?token=` URLs** for password-reset + parent magic links (keep one-time tokens out of logs).
- [ ] Add explicit test/comment that **`dob` is never updatable** (mirror the `country_code` immutability), so a future edit-profile feature can't reopen the consent-age input.
- [ ] **Rotate `CRON_SECRET`** — value was pasted in plaintext during earlier debugging.

### Strong fundamentals (no action)
Consistent object-level access control (no IDOR), self-scoped data export (no sibling leakage), textbook OIDC (alg pinning, iss/aud/nonce, email_verified before linking), CSRF double-submit + correct cookie flags, constant-time secret compares, fail-closed LLM moderation, account lockout, Stripe webhook signature verified, `.env` hygiene clean, `country_code` immutable.

---

## 3. Premium Level-2 content + new premium modules

**Verdict:** Strong investment area. Data model already supports it (Level 2 = second `Level` row, `is_premium=True`, under each module; idempotent seed handles it). Author only after brainstorm/greenlight.

### Level 2 outlines for the 12 existing modules (3–5 deeper lessons each)
- [ ] What is a Stock? → **Valuing a Company** (price vs value, P/E, reading a chart, dividends)
- [ ] Compound Interest → **The Maths of Growth** (Rule of 72, compounding frequency, inflation as reverse-compounding)
- [ ] What is a REIT? → **Property Investing Deeper** (yield, residential/commercial/industrial, rates impact)
- [ ] Budgeting → **Building a Safety Net** (emergency funds, sinking funds, zero-based budgeting)
- [ ] Needs vs Wants → **Spending Psychology** (lifestyle creep, marketing tactics, 24-hour rule)
- [ ] Risk & Diversification → **Measuring & Managing Risk** (volatility, correlation, allocation, rebalancing)
- [ ] Crypto → **Blockchain Deeper** (consensus, wallets/keys, stablecoins/NFTs, scam-spotting)
- [ ] Taxes → **Tax-Smart Saving** (ISA/Junior ISA; US 401k/IRA, HK MPF via country_codes; CGT vs income)
- [ ] Debt & Credit → **Mastering Credit** (score mechanics, minimum-payment trap, utilisation, good debt)
- [ ] Side Hustle → **Growing a Small Business** (pricing for profit, customer retention, reinvest vs cash)
- [ ] Revenue/Costs/Profit → **Reading the Numbers** (profit margin %, break-even, cash flow vs profit)
- [ ] First Paycheque → **Building Your Financial Future** (workplace pensions + employer match, pay-yourself-first)

### New premium modules (advanced; suggested age bands)
- [ ] **ETFs & Index Funds** (13–18) — graduation from single-stock thinking; high retention value
- [ ] **Inflation & the Value of Money** (12–18) — real vs nominal returns
- [ ] **Behavioural Biases — Your Brain & Money** (13–18) — loss aversion, FOMO, herd mentality
- [ ] **Pensions & Retirement** (14–18) — compounding + tax wrappers at full power
- [ ] **Reading Financial News & Spotting Scams** (12–18) — media literacy + safeguarding capstone

### Guardrails
Concept-only (no "buy X", no personalised advice); play money in simulator; localise figures via `country_codes`; scaffold card→video→quiz→scenario; require Level 1 before Level 2; LLM reinforcement still passes `moderate_output`. The Scams/News + Biases modules turn safety into curriculum (on-brand for a kids' app).

---

## 4. Subscription pricing

**Recommendation: $4.99/mo or $39.99/yr (~33% annual discount), free tier + short free trial.**

### Rationale
- **Market band:** InvestiKid is *pure-education*, not a *card app*. Don't anchor to Greenlight/GoHenry/Goalsetter ($4–25, bundle a physical card). Comparables = AI-tutor/edtech: Khanmigo $4/mo, Duolingo Super ~$7/mo, with free rivals (Zogo, Khan) setting the floor → credible band **$4–8/mo, $40–80/yr**.
- **Costs are tiny:** R2 has zero egress (video effectively free); open-source LLM (together.ai) ≈ **$0.03/active user/mo typical, $0.10–0.15 heavy** → 1–4% of revenue, **~95%+ gross margin**.
- **Profitability = volume vs a small fixed baseline** (Railway+Vercel+Postgres ~$10–40/mo early → ~$100–250/mo at thousands). **Break-even ~45–75 paying subscribers.**

### Structure & levers
- [ ] Lead with **annual** ($39.99) for retention/cash flow.
- [ ] **Free tier** = lessons + simulator; **paywall AI Coach + premium Level-2 content** (matches existing AI-gated architecture).
- [ ] **Free trial** 7-day (edtech norm) or 30-day (kids-finance norm).
- [ ] **Family plan** ~$7.99/mo or $59.99/yr (up to ~3–4 kids).
- [ ] **School/B2B** licensing — highest margin, hedge vs free competition.
- [ ] **Regional price tiers** (not FX): US $4.99 · UK £3.99/£29.99 · HK ~HK$38; set via App Store Connect price points.
- [ ] Enrol in **Apple Small Business Program** (15% vs 30% under $1M/yr); Web/Stripe avoids the cut where allowed.
- [ ] **Instrument real Coach/moderation token counts in beta** to confirm the cost model.

---

## 5. App icon concept

**Pick: "Penny in a sprouting coin."** Front-facing Penny on a sky-blue→indigo gradient rounded-square, with a single gold coin sprouting a small green leaf (money-grows / compounding cue). Says *kids* + *finance that grows* in one glance; distinct from generic card/piggy-bank icons; legible at 60px. Keep to 2–3 colours, no text, no fine detail.

Alternatives:
- Minimalist growth-arrow monogram (stylised £/$ or candlestick), white on gradient — more grown-up, weaker kid-warmth.
- Penny's face on the top coin of an ascending stack — "stacking savings", slightly busier small.

- [ ] Generate SVG/PNG mockups of the chosen concept at icon resolution for home-screen comparison.

---

## Suggested sequencing (when we resume)
1. **Security fix** (parent logout/session revocation) — pre-beta blocker.
2. **Flow cleanup** (vocabulary, Home next-action, Progress re-skin) — low effort, high clarity.
3. **Engagement bets** (notifications + streak defense → friends/class leaderboards → age-tier mode).
4. **Premium content** build-out (justifies the paywall) + **pricing/paywall UI**.
5. **App icon** mockups.
