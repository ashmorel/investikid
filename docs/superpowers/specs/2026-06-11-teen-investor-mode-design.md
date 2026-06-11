# W5 — Teen "Investor Mode" — Design Spec

**Date:** 2026-06-11 · **Status:** Approved (design) — pending implementation plans
**Repo:** `ashmorel/investikid` · branch `testing`
**Roadmap:** Phase 2, workstream W5 (`docs/2026-06-10-best-in-class-roadmap.md`). Responds to the review's "the app needs a more mature tone for 15-18 and more real-life financial content".

## Decisions (locked with user)
1. **Restrained skin** — tone + density pass via config knobs; same brand palette; NO theme fork.
2. **Visible label + parent override** — an "Investor" identity label in the teen UI; mode auto by DOB (boundary 14) with a per-child parent override (Auto / Explorer / Investor).
3. **Three new 14+ modules** — Student Money, Investing for the Long Term, Your Brain on Money.

## Current state (verified)
- `backend/app/services/age_tier.py`: `AGE_TIER_BOUNDARY = 14`; `User.age_tier` is a live property from `dob` (`app/models/user.py` ~78). Tier drives Coach LLM register, hero greeting (`frontend/src/lib/tierCopy.ts`), encouragement lines, Penny hero size (`tierConfig` in `frontend/src/lib/ageTier.ts`: 44 vs 32), module ordering (`tierModuleOrder.ts`). **Silent** — no label, no override, Home-only differentiation.
- `Module.min_age`/`max_age` exist and are enforced by the recommendation hard-filters and content gating; **no seed module uses them** today.
- Modules carry (since W3/W4): `standards_alignment`, `sources`, `learning_objectives` per level, `conversation_prompt`. New modules must ship with ALL of these.

## W5a — Visible mode + parent override

### Backend (one chained migration)
- `users.tier_override: String(16) | None` (values `explorer` | `investor`; NULL = auto).
- `User.age_tier` property: `tier_override or (DOB-derived tier)`. Single source of truth — Coach, copy, ordering all inherit.
- Parent endpoint: extend the existing parent→child management surface (PATCH child) to accept `tier_override` (validated enum-or-null); only the linked parent may set it. Parent child payloads expose `age_tier` (effective) + `tier_override`.
- Child session payload (`/auth/me` or child session) already exposes `age_tier` — unchanged consumers.

### Frontend
- **Identity label:** a small "Investor" chip in the child header/hero, investor tier only (explorer sees nothing new). Quiet styling (brand tokens), not a button.
- **Tone/density pass (config-driven):** extend `tierConfig` with knobs — `density: 'cozy'|'compact'`, `celebrationStyle: 'big'|'subtle'`, `showPennyCelebrations: bool` — and apply: Lessons page headers, module-complete celebration (investor: subtle banner, no Penny takeover), toast copy via `tierCopy` additions, card spacing on Home/Lessons (compact for investor). Penny: header-only and 32px for investors (already partly true); no celebrating Penny in investor flows.
- **Parent dashboard:** "Experience mode" select per child (Auto (recommended) / Explorer / Investor) with a one-line explainer; wired to the PATCH; shows the effective mode.
- A11y: chip has accessible name; selects labelled; axe-clean.

### Testing (W5a)
Backend: override property precedence (set/unset, both values); PATCH validation (bad value 422, non-linked parent 403/404); payload fields. Frontend: chip shows only for investor; density/celebration knobs render per tier; parent control round-trips; axe.

## W5b — Three 14+ modules (content)

All gated `min_age=14`, `country_codes: []`, 3 levels each (L1/L2 free, L3 premium by position), ~7 lessons per level (2 cards + 4 quizzes + 1 scenario pattern), plus the full credibility envelope: `learning_objectives` per level, `standards_alignment`, `sources` (official bodies), `conversation_prompt`.

1. **Student Money: University & Beyond** (`topic: budgeting` or new `student` topic — decide at plan time against the ModuleTopic enum) — student finance & loans (UK-first, US note), rent/bills/deposits, part-time work + payslips recap, budgeting away from home; L3: overdrafts/credit at uni, scam-spotting (housing/job scams). MaPS *How to manage money*; J$ II Spending + V Managing Credit.
2. **Investing for the Long Term** (`topic: stocks` family or `investing`) — wrappers (ISA/Junior ISA, pension, 401k-style), index funds vs picking, decades-horizon compounding, fees; L3: asset allocation by horizon, drawdowns & staying invested. MaPS *Understanding the important role money plays*; J$ IV Investing.
3. **Your Brain on Money** (`topic: risk` family or `behaviour`) — FOMO & hype, loss aversion, herd behaviour, anchoring/advertising, why we overspend; L3: building personal money rules, reflection habits. MaPS *Managing risks and emotions associated with money*; J$ VI Managing Risk.

Process = the proven rollout pipeline: parallel AI drafting agents (one per module, grounded in existing seed style + the teen "investor" register), programmatic shape validation, **one assembled review doc → user spot-review → deterministic seed insertion**. Standards strands quoted from the published frameworks (already verified in W3b). Maths in examples verified. UK-context, kids-safe, every scam scenario routes to checking with a trusted adult (teen-appropriate phrasing: "someone you trust" rather than "grown-up").

### Testing (W5b)
Seed shape tests (the generic ones already cover new modules automatically); min_age gating test (13-year-old doesn't receive them, 15-year-old does — via recommendations and module list); idempotent re-seed; prompts/objectives/standards present.

## Sequencing
W5a → W5b. Each its own implementation plan + subagent build on `testing`.

## Out of scope
Theme fork; changing the 14 boundary; new gating mechanics (min_age already enforced); simulator changes (that's W6); localisation; changing Penny's design.

## Risks
- **Tone drift in teen content:** drafting agents get explicit register guidance ("confident, plain, never childish, no talking-down") + user spot-review.
- **Topic enum:** new topics may require widening a ModuleTopic literal/enum in schemas — plan must check `app/schemas/content.py::ModuleTopic` and admin validation before choosing topic strings.
- **Override misuse:** only linked parents can set; child UI never exposes the control.
