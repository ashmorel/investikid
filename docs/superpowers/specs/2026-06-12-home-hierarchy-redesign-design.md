# Home Hierarchy Redesign (M3) — Design Spec

**Date:** 2026-06-12 · **Workstream:** M3 of `docs/2026-06-12-market-leader-roadmap.md`
**Figma exploration:** "M3 — Home Hierarchy Exploration (2026-06-12)" page in file `h5xrUTiNDZqqhu4pvYprqc`.
**Decision (owner-approved):** Variant A's hierarchy as the base, Variant B's combined stats card as the single secondary element, Variant C as the investor-tier skin of the same layout.

## Goal

The external review's sharpest UX critique: child Home has eight competing surfaces (hero,
stats bar, level progress, premium upsell, portfolio snapshot, review banner, achievements
strip, modules grid). Redesign Home around **one primary action** — the Continue hero — so a
child always knows the one thing to do next. Same structure for both age tiers; tone and
density flip via `tierConfig`.

## New Home composition (top → bottom)

1. **Greeting** — unchanged `HomeHero` greeting row (Penny avatar + speech bubble; investor
   tier already shows TierChip). New `tierConfig` knob `showPennyAvatar`: explorer `true`,
   investor `false` (investor renders the greeting as a plain heading line — Variant C).
2. **Continue hero (dominant)** — the existing `HomeHero` CTA card, enlarged: overline
   ("CONTINUE LEARNING" / investor "CONTINUE"), `moduleTitle` as the headline (~text-xl
   extra-bold), `lessonLabel` meta line, full-width CTA button. Explorer: brand-gradient
   card, rounded-3xl, shadow. Investor: flat white card, thin border, rounded-xl, indigo
   solid CTA, small progress feel — via new `tierConfig` knob `heroVariant:
   'playful' | 'flat'`. `caught_up` / `review` modes keep their existing copy inside the
   same card shell.
3. **Combined stats card** (new `StatsCard`) — replaces BOTH `StatsBar` and
   `LevelProgressCard` on Home (both are Home-only today; the old components are deleted).
   One white card: row 1 = `⭐ Level N` left, `🔥 streak · 🛡️ freezes` right (investor: no
   emoji, plain text labels); row 2 = XP progress bar to next level; row 3 = "X / Y XP to
   Level N+1" caption. Reuses the level/xp maths currently in `LevelProgressCard`.
4. **Quick-links row** (new `QuickLinksRow`) — one horizontal row of small tappable chips
   under a tiny "WHILE YOU'RE HERE" label, replacing the three full-width cards:
   - **Portfolio** chip — `usePortfolio` total (formatted, currency-aware) → `/simulator`.
     Hidden when no portfolio value (matches today's conditional).
   - **Review** chip — `recs.review_summary.due_count` ("N to review", amber tint) →
     `/progress`. Hidden when due_count = 0.
   - **Badges** chip — earned/total counts from `useBadges`/`useAllBadges` → `/stats`.
   Chips are `<Link>`s with ≥44px tap height (iOS golden rule), text ≥ 12px.
5. **Premium upsell (slim)** — non-premium children only: `PremiumUpsellCard` is rewritten
   in place as a single-line row ("✨ Unlock all levels & the AI coach" + CTA + dismiss) —
   verified Home-only, so no second variant is needed. Dismissal + paywall-open behaviour
   unchanged.
6. **Browse all modules** — the existing gradient button → `/lessons`. **The modules grid
   leaves Home entirely** (the Learn tab is the browsing surface; the next-lesson resolver
   already drives "what's next").

Removed from Home: `StatsBar`, `LevelProgressCard` (deleted; merged into `StatsCard`),
`PortfolioSnapshotCard`, `ReviewBanner`, `AchievementsStrip`, modules grid + `ModuleTile`
usage (all four components stay in the codebase only if referenced elsewhere; delete any
that become orphans — currently `PortfolioSnapshotCard`, `ReviewBanner`,
`AchievementsStrip` are believed Home-only ⇒ delete, verify with grep at build time).

## tierConfig additions

```ts
heroVariant: 'playful' | 'flat'   // explorer: playful (gradient), investor: flat
showPennyAvatar: boolean          // explorer: true, investor: false
chipEmoji: boolean                // explorer: true, investor: false (quick-link chips)
```

Existing knobs (`density`, `celebration`, `showTierChip`, `pennyHeroSize`) unchanged.
Investor additionally renders quick-link chips denser (existing `density` knob) — no new
mechanism. Gates on `useAgeTier()` exactly as today (live DOB tier, parent override server-side).

## Data / API

No backend changes. All data already fetched by Home today; the redesign only recomposes
it. Net effect: Home drops two card-render queries' worth of DOM, no new endpoints.

## Accessibility (WCAG 2.2 AA — non-negotiable)

- Keep `h1.sr-only` "Your learning home"; hero stays a labelled `section`; quick-links row
  is a `nav` with `aria-label="Shortcuts"`.
- All chips: real links, visible focus ring, ≥44×44 tap target, text contrast AA on tints.
- XP bar: `role="progressbar"` with `aria-valuenow/min/max` + visible caption.
- Emoji in chips/stats `aria-hidden` with text alternatives (existing convention).
- New components each get a `vitest-axe` test; update `tests/a11y/child-core` group.
- Reduced-motion: hero keeps existing `useReducedMotion` gating.

## Edge cases

- **Loading:** hero keeps its pulse skeleton; StatsCard renders its zero-state (Level 1,
  0 XP) until progress loads; QuickLinksRow appears as data arrives (below the fold —
  minor shift acceptable, chips are conditional anyway).
- **caught_up:** hero shows the existing "All caught up" celebration; Review chip likely
  visible → natural next action.
- **New account (no progress, no portfolio):** Home = greeting + hero ("Start your first
  lesson") + StatsCard (Level 1, 0 XP) + Browse button. No empty chip row (row hides when
  all chips hidden).
- **Premium child:** no upsell row (matches today's `is_premium` gate).
- **Offline:** existing `OfflineNotice` behaviour unchanged; chips render from cached
  queries (query persistence already in place).

## Testing plan

- Unit: `StatsCard` (level maths, freeze display, investor no-emoji), `QuickLinksRow`
  (conditional chips, hrefs, currency formatting), slim `PremiumUpsellCard` variant,
  `HomeHero` heroVariant flip, Home composition (renders exactly the six sections in order;
  asserts modules grid gone).
- A11y: axe on Home (both tiers) + each new component.
- Update existing Home/StatsBar/LevelProgress tests (move/merge assertions into StatsCard).
- Suite gates: `npx tsc -b`, `npm run lint`, `npm test`, `npm run build`; then
  `npx cap sync ios` (copy-only change) — USER Xcode rebuild to see on device.

## Out of scope (deferred)

- CTA tap-through measurement → M4 (analytics) — note: M4 should instrument the hero CTA
  and chip taps on day one.
- Learn-tab/module-list changes (Variant C's list rows) — separate pass if teen testing
  (M10) asks for it.
- Penny cosmetics / theme hooks (M8).
