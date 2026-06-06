# Age-Tier Mode (Design Spec)

**Date:** 2026-06-05
**Status:** Approved (design); ready for implementation plan
**Origin:** Product-review item 3, sub-project **3C** (engagement bets; after 3A re-engagement ✅, alongside 3B social). Addresses the "10-vs-18 tension" — the app's tone skews young while content skews older.
**Scope:** Backend (derive + expose tier, tier-aware LLM prompts) + frontend (tier-aware copy, mascot prominence, module ordering). No new data collected; no new privacy surface.

---

## Problem

A 10-year-old and a 17-year-old get the same experience: emoji-heavy, mascot-forward, "ask a grown-up" copy wrapped around stocks/crypto/tax content. The teen feels patronized; the younger kid gets investing-first ordering. The DOB to segment them is already collected — nothing downstream uses it.

## Decisions (locked with the user)

- **Two tiers, DOB-derived:** `explorer` (10–13, i.e. under 14) vs `investor` (14–18, i.e. 14+). Boundary constant `AGE_TIER_BOUNDARY = 14`.
- **Silent:** the tier adapts the experience but is **never labelled** in the UI (a visible "you're a kid" badge would itself patronize).
- **No manual override** in v1 — derived from DOB only.
- **v1 dimensions:** (1) tone/copy register, (2) mascot prominence, (3) default module ordering. **Simulator emphasis is deferred** (overlaps the separate "wire in the Simulator" backlog item).
- **Single source of truth:** tier derived once on the backend (`app/services/age_tier.py`), exposed on the child `Me` (`UserProfile`), and reused for the LLM prompts. The frontend reads `me.age_tier`; it does NOT re-derive from `dob`.

## Non-goals

- No Simulator foregrounding, no manual tier toggle, no visible tier label/badge (all v1-deferred or rejected).
- No change to the backend recommender's scoring (it already age-filters via module `min_age`/`max_age`); module *ordering* here is a frontend display concern only.
- No new DB column (tier is computed from the existing `dob`).
- The existing premium `TierBadge` is unrelated and untouched (different "tier").

---

## Architecture

### Tier derivation (backend, single source of truth)

New `app/services/age_tier.py`:
```python
from datetime import date
from typing import Literal

AGE_TIER_BOUNDARY = 14  # age (inclusive) at which a learner becomes "investor"
AgeTier = Literal["explorer", "investor"]

def age_in_years(dob: date, today: date) -> int: ...        # full years
def age_tier(dob: date, today: date) -> AgeTier:
    return "investor" if age_in_years(dob, today) >= AGE_TIER_BOUNDARY else "explorer"
```
(If an equivalent age-in-years helper already exists for consent, reuse it rather than duplicating.)

Expose on the child profile. `UserProfile` (`app/schemas/user.py`) gains `age_tier: AgeTier`. The cleanest single-source wiring: add a read-only `age_tier` **property** on the `User` model that calls `age_tier(self.dob, date.today())`, so every `UserProfile` built from a user (via `from_attributes`) auto-populates it — `GET /users/me`, `PATCH /users/me`, and the `/register` success response all get it with no per-site code. (The implementer confirms whether `UserProfile` is built via `model_validate(user)`; if it's constructed field-by-field instead, set `age_tier=user.age_tier` at each site.)

Frontend `Me` type (`src/api/auth.ts`) gains `age_tier: 'explorer' | 'investor'`.

### Dimension 1 — Tone/copy register

**Templated copy (frontend).** A centralized register map (`src/lib/tierCopy.ts`) keyed by tier supplies the variants used by the hero greeting (`lib/homeHero.ts` `buildHeroGreeting`) and Penny's rotating encouragement lines (`LessonChrome`). Explorer = warm, light emoji ("Awesome job! 🎉"); investor = cleaner, cool, minimal emoji ("Nice work."). `buildHeroGreeting` takes the tier; `HomeHero` passes `me.age_tier`.

**LLM prompts (backend).** `home_greeting_service._build_messages` and `coach_service`'s system prompt each take the tier and append a register directive:
- explorer: "The learner is 10–13. Be warm, playful, simple, and encouraging; at most one light emoji; no jargon."
- investor: "The learner is 14–18. Be encouraging but mature and concise; no baby-talk, minimal/no emoji; you can use real financial terms."
The tier is taken from the authenticated `current_user.age_tier` (server-trusted), NOT from any client payload. Output still passes `moderate_output`. The directive text lives as named constants alongside the prompt (one place to retune).

### Dimension 2 — Mascot prominence

A small frontend `tierConfig` (in `src/lib/ageTier.ts`, alongside a `useAgeTier()` reading `me.age_tier`) exposes per-tier presentation knobs, e.g. `{ pennyHeroSize: number; playful: boolean }` — explorer gets a larger hero Penny and the playful flourishes; investor gets a smaller, subtler Penny. `HomeHero` (and optionally the lesson encouragement frequency) read from it. Config-driven so the sizes/flags are one-line tunable.

### Dimension 3 — Default module ordering

A centralized `topic → priority` map per tier (`src/lib/tierModuleOrder.ts`) provides a comparator used to order the module grid (`Home.tsx`) and the module list (`Lessons.tsx`). Investor surfaces investing topics first (stocks, crypto, risk, REIT); explorer surfaces foundations first (budgeting, needs-vs-wants, savings). Ties and unmapped topics fall back to the existing `order_index`. Frontend display-ordering only — module identity, routes, and backend ordering are unchanged.

## Always-live (no frozen tier) — a hard requirement

The tier MUST track the child's real age automatically; it is never captured at signup or
persisted. Guarantees:
- **No `age_tier` DB column.** The tier is computed on demand from the existing `dob` via
  `date.today()` every time it's read (the `User.age_tier` property), so it can never go
  stale. A child who turns 14 becomes `investor` on their very next request — no job, no
  migration, no re-save.
- **Every age-dependent surface keys off the same live tier**, so they all flip together:
  templated copy register, Penny prominence, module ordering (all read `me.age_tier`), and
  the LLM register directives (read `current_user.age_tier`). There is no second, divergent
  age source anywhere.
- **Frontend freshness:** the FE reads `age_tier` from the `['me']` query; on the next fetch
  after a birthday (a reload or the normal session refresh) the whole experience updates.
  No client-side caching of the tier beyond the standard `['me']` query lifetime.

## Easy to retune later — a hard requirement

Beyond "no magic numbers," the design is structured so a future change is a one-place edit:
- Move the boundary, add a third tier, or rename tiers → edit `age_tier.py` (the `AgeTier`
  type + `age_tier()`); the schema field and all readers follow from the single source.
- Change a register's wording, mascot sizes, or module priorities → edit `tierCopy.ts`,
  `ageTier.ts` (`tierConfig`), or `tierModuleOrder.ts` respectively — no component edits.
- Change the LLM tone directives → edit the named prompt-directive constants in one place.
Tests reference these constants/sources (not duplicated literals) so retuning a value
doesn't silently break an expectation.

## Data flow

1. Backend computes `age_tier` from `User.dob` → returned on `Me`.
2. FE reads `me.age_tier` → drives templated copy register, Penny prominence, and module-list ordering.
3. LLM greeting/Coach endpoints read `current_user.age_tier` → inject the register directive into the system prompt → moderated output.

## Error handling & edge cases

- **Age < 10 / very young:** still `explorer` (boundary only splits at 14); fine.
- **Missing/odd `dob`:** `dob` is non-null (`User.dob`), so the tier always resolves; if a future nullable path appears, default to `explorer` (the safer, gentler register).
- **Birthday crossing 14:** tier flips naturally on the next request after the 14th birthday (uses `date.today()` server-side). No migration needed.
- **Premium AI greeting vs templated:** both honor the tier (AI via prompt, templated via `tierCopy`), so the register is consistent whether or not the child is premium.

## Testing

**Backend (pytest, `loop_scope="session"` + fixtures):**
- `age_tier` boundary matrix: age 13 → explorer, 14 → investor, 17 → investor, 9 → explorer (use fixed `dob`/`today`).
- `GET /users/me` returns `age_tier` matching the user's DOB (one explorer user, one investor user).
- The greeting + coach prompt builders include the correct register directive per tier (assert the directive substring appears for explorer vs investor).

**Frontend (vitest + vitest-axe):**
- `tierCopy` returns the right register per tier; `buildHeroGreeting` produces tier-appropriate text.
- `tierModuleOrder` comparator orders a sample module set correctly for each tier (investing-first vs foundations-first), falling back to `order_index`.
- `HomeHero` renders the tier-appropriate Penny size (explorer vs investor), axe-clean.
- Existing greeting/HomeHero/Lessons tests stay green.

## Configurability (single source of truth)

- Backend: `AGE_TIER_BOUNDARY` + tier logic in `age_tier.py`; the two LLM register directives as named constants by the prompt builders.
- Frontend: `tierCopy.ts` (register copy map), `ageTier.ts` (`tierConfig` mascot knobs + `useAgeTier`), `tierModuleOrder.ts` (topic-priority map). No inline tier literals/copy in components — all read from these.

## Constraints

- WCAG 2.2 AA; iOS inputs ≥16px, no `maximum-scale` (this is copy/ordering/sizing — no input changes). It's a kids' app — keep safe; LLM output still moderated.
- Backend verify: `ruff` + `pytest`. Frontend: `npx tsc -b`, `npm run lint`, `npm test` (vitest + vitest-axe), `npm run build`.
- Commit to `main`; end messages with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Railway + Vercel deploy on green CI (6 jobs). No `.env` access. iOS shows the same web bundle → a `cap sync ios` at close-out (no native change).

## Alternatives considered

- **Frontend-derived tier from `dob`:** lowest effort (dob is already on `Me`), but duplicates the boundary in two languages and can't feed the server-side LLM prompts. Rejected in favour of one backend source exposed as `age_tier`.
- **A visible tier badge / manual mode switch:** rejected for v1 — a label risks patronizing, and a switch is YAGNI when DOB is reliable. Could revisit if users ask.
- **Backend module reordering:** rejected — the recommender already age-filters; reordering the *display* on the FE is lower-risk and keeps module identity/order stable.
