# W5a — Visible Investor Mode + Parent Override — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Make the investor tier visible (an "Investor" chip), deepen the tone/density differentiation via config knobs, and give parents a per-child experience-mode override.

**Spec:** `docs/superpowers/specs/2026-06-11-teen-investor-mode-design.md` (W5a section).

**Verify:** backend `ruff` + `pytest` (venv `/Users/leeashmore/Local Repo/.venv`); frontend `npx tsc -b && npm run lint && npm run test && npm run build`. Branch `testing`; explicit `git add`; commit suffix `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Verified facts:**
- `app/services/age_tier.py` (`AGE_TIER_BOUNDARY=14`), `User.age_tier` property at `app/models/user.py` ~78.
- Parent per-child action pattern to mirror: `POST /parent/children/{user_id}/freeze` / `/premium` (`app/routers/parent.py:141/156`) — copy their linked-parent auth checks exactly.
- Alembic head after W4: `8b2f4c1d9e6a` (confirm with `alembic heads`).
- FE tier plumbing: `frontend/src/lib/ageTier.ts` (`tierConfig`, `useAgeTier`), `tierCopy.ts`, `HomeHero.tsx` (Penny size knob), `Lessons.tsx`. Parent child UI: `ChildCard.tsx` (find via grep) hosts freeze/premium controls to sit beside.

### Task 1 (BE): `tier_override` column + property + parent endpoint
- Migration (chained off current head): `users.tier_override String(16) NULL`.
- `User.age_tier`: return `self.tier_override` when set (validate at write, not read), else DOB-derived.
- `POST /parent/children/{user_id}/tier` body `{tier_override: 'explorer'|'investor'|None}` (pydantic Literal|None) — mirror freeze's auth (linked parent only); response includes effective `age_tier` + `tier_override`. Add both fields to the parent children/analytics payload (wherever freeze status is exposed — match).
- Tests: property precedence (set explorer on a 16yo → explorer; clear → investor); endpoint happy/422 bad value/unauthorized parent; payload fields.
- Commit `feat(w5a): per-child tier override (schema + parent endpoint)`.

### Task 2 (FE): Investor chip + tone/density knobs
- `tierConfig` grows: `{ pennyHeroSize, density: 'cozy'|'compact', celebration: 'big'|'subtle', showTierChip: bool }` (investor: 32/compact/subtle/true; explorer: 44/cozy/big/false).
- "Investor" chip: small brand-token pill near the hero greeting (aria-label "Investor mode"), rendered when `showTierChip`.
- Apply knobs: Home + Lessons card gap (compact → tighter spacing class), module-complete celebration in `Module.tsx` (subtle → plain banner, no Penny, no emoji burst — reuse existing banner styling), 2-3 investor toast/copy strings via `tierCopy` where explorer copy is emoji-heavy.
- Tests: chip only for investor; subtle celebration for investor / big for explorer; spacing class per tier; axe-clean both tiers.
- Commit `feat(w5a): visible Investor chip + tier tone/density knobs`.

### Task 3 (FE): Parent "Experience mode" control + regression + push
- Child card/settings: select Auto (recommended)/Explorer/Investor → `POST /parent/children/{id}/tier` (new api client fn); shows effective mode; optimistic update + toast, mirroring freeze/premium controls.
- Tests: renders current state, change PATCHes correct body, axe.
- Full regression both stacks; push; watch CI (re-run once on the known PyPI pip-audit flake).

## Self-review
Spec W5a fully covered (migration, property, endpoint, chip, knobs, parent control). No theme fork; boundary unchanged; child UI never shows the control.
