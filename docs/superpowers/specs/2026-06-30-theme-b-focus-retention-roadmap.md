# Theme B — Focus & Retention — Roadmap / design draft

**Date:** 2026-06-30
**Status:** Draft roadmap (ready to turn into per-item SDD plans when build starts)
**Source:** Codex beta review (focus = the #1 named risk) + the Beta→9.5 programme.

## Goal

Theme A proved the app *teaches*. Theme B makes it *get used and rated*. Two levers:
**focus** (one obvious daily action so a feature-rich app doesn't overwhelm) and **retention/
delight** (the things that bring kids back and earn 5★). These are the most direct moves on
"top-rated" — and several are small. Four items: **B1 focus**, **B3 arcade-subordination**,
**B5 ratings flywheel**, **B6 streak beats**.

> Note: B2 (a streak/daily-goal engine) is NOT needed — the existing engine is already
> Duolingo-grade (configurable goal 10/30/50, earned freezes cap 2, UTC reset, push, multi-
> activity). B6 is just the missing *emotional beats* on top of it.

---

## B5 — Ratings & reviews flywheel  *(smallest, most direct "top-rated" lever — do first)*

**Why:** the single most direct input to App Store/Play rating, and currently nobody asks.
**What exists:** no in-app-review plugin (grep: none). Delight signals already exist server-side:
streak milestones (`content_service`), mastery level-ups, daily-goal-met (`xp_service`).
**Design:**
- Add a Capacitor in-app-review plugin (e.g. `@capacitor-community/in-app-review` / Capawesome's
  rate plugin) → call the **native OS review prompt** (StoreKit `requestReview` / Play In-App Review).
- A small client gate `shouldAskForReview()` fires the prompt **only at a delight moment** —
  a streak milestone (7/14/…), a mastery level-up, or a strong daily-goal run — **never** after a
  wrong answer, a crash, or a paywall. Self-rate-limit (one ask per long cooldown; persist
  "asked" in storage); the OS also throttles, so we just pick the *moment*.
**Key decisions (AD-B5):**
- *Which trigger(s)?* Lean: **streak milestone (7-day) OR first mastery level-up**, whichever first.
- *Cooldown?* Lean: ask at most once per ~60 days, and never within the first session.
**Size:** small. **Native-visible** (plugin → needs a build).

## B6 — Streak emotional-beat polish  *(cheap retention dopamine)*

**Why:** the engine is great but spends its best moments silently. The early streak audit found
the **freeze-saved** moment is invisible — a missed dopamine hit Duolingo makes a huge deal of.
**What exists:** `streak_count`, `streak_freezes` (earned every 7 days, cap 2), silent consumption
in `streak_after_activity`; `virtual_coins` (user.py:132).
**Design (three beats):**
1. **"Streak saved!" celebration** — when a freeze is consumed, return that signal (a `freeze_used`
   bool on the activity/progress response) and the client fires a celebratory toast/animation
   ("Your 🔥 streak was saved!").
2. **Freeze visibility / countdown** — show the held freeze count + "next freeze in N days" on the
   streak UI (StatsCard), so the earn-loop is visible.
3. **Coin-funded streak repair** — when a streak just broke, offer to **spend earned coins** to
   restore it (on-theme, no real money; coins already exist). Backend: a `POST /streak/repair`
   that, within a short grace window after a break, restores `streak_count` for a coin cost
   (idempotent, server-validated window + balance). Client: the offer + confirm.
**Key decisions (AD-B6):**
- *Repair grace window* (e.g. repair allowed within 2 days of a break?) and *coin cost*.
- *Does the freeze-saved signal need a new response field* or can the client infer it (lean: add an
  explicit `freeze_used` to the completion/progress payload — don't make the client guess).
**Size:** medium (3 sub-features; #3 has a backend endpoint, no migration if repair is computed
from existing fields). **Native-visible.**

## B1 — One canonical "Today" action  *(the #1 named risk — focus; design-heavy)*

**Why:** Codex flagged focus twice. A 12–18 "bite-sized like Duolingo" app needs **one obvious
daily action**; Home is currently a pile of cards (Hero, Revise, Arcade-daily, Featured-drop,
Stats, shortcuts, premium). Every screen should answer "what do I do next?".
**What exists:** the Figma-first Home redesign already grouped Home into *learning / play /
shortcuts* zones; `HomeHero` has a Start/Continue-next-lesson hero. So the bones are there — B1 is
making the daily action **singular and unmissable**, and demoting everything else.
**Design:**
- Home opens to **ONE primary CTA**: *today's lesson* (or *review* when caught up), tied to the
  **daily goal + streak** (the Duolingo pattern: one lesson advances the goal + keeps the streak).
- Everything else (Arcade, Shop, markets, groups) becomes clearly secondary — below the fold /
  smaller / behind the primary action.
- Audit every child screen against "what do I do next?" and remove dead-ends.
- **Figma-first** (per the standing rule for non-trivial UI): mock the focused Home → approve →
  implement. (Re-uses the design-system file `h5xrUTiNDZqqhu4pvYprqc`.)
**Key decisions (AD-B1):**
- *What exactly is "today's action" when the child is fully caught up* (no new lessons + nothing
  due)? Lean: a "practice/MoneyWord" suggestion, not an empty state.
- *How hard to demote play/shop* — collapse vs below-the-fold vs a separate tab? Lean: keep on Home
  but visually subordinate, not removed (kids like the play surface — B3 governs its weight).
**Size:** medium (design-led; mostly IA/layout, not new systems). **Native-visible.**

## B3 — Arcade-subordination rule  *(a guardrail; can run alongside)*

**Why:** the Arcade/Shop/coin loop must *reinforce* finance learning, not become "a coin economy
with finance attached" (a real one-star-review risk with parents).
**What exists:** `ARCADE_DAILY_XP_CAP = 25` (arcade gives ≤25 coins/day); lessons award coins
uncapped-per-lesson → **learning is already the larger coin source**. Quiz Rush already prefers
unlocked concepts. And A1 gives us a **concept taxonomy** to tie games to.
**Design:**
- **Write the rule** (design-system / AGENTS.md): every arcade game maps to a tagged concept;
  **learning is the primary path to coins**; cosmetics are *rewards for learning*, never the point.
- **Verify/keep the economics** so lessons ≫ arcade as a coin source (the 25/day cap already does
  this — confirm and document the ratio; tighten only if data shows grinding).
- **Tie games to concepts** — Quiz Rush draws from the child's **weak concepts** (now that
  `ConceptMastery` exists from A2 U5) so play *reinforces* gaps, not random trivia.
**Key decisions (AD-B3):**
- *Gate arcade behind a completed lesson, or just keep the coin cap?* Lean: **don't gate** (fun
  matters) — rely on coin economics + concept-tying + the written rule.
**Size:** small (a rule + economics confirmation + a concept-tie tweak to Quiz Rush). Mostly
backend + copy; minimal native.

---

## Recommended sequence

1. **B5 ratings flywheel** — smallest, most direct rating lever; ship early (rides the next native build).
2. **B6 streak beats** — cheap, high-dopamine retention; the freeze-saved celebration is the
   standout. (B5 + B6 are the two that most directly lift the rating.)
3. **B1 focus pass** — the #1 risk; Figma-first, so it spans a design + an implementation step.
4. **B3 arcade-subordination** — a guardrail; can land alongside B1 (they both touch the play surface).

Plus, in parallel and not strictly engineering: the **beta-as-research instrumentation** (segment
the cohort 8–10 / 11–13 / 15–18; measure activation, completion, return rate, and — using Theme A
— concept retention). That's what turns the beta into evidence.

## Open decisions to lock before building (per item above)
- **AD-B5:** trigger(s) + cooldown.
- **AD-B6:** repair grace window + coin cost; explicit `freeze_used` signal.
- **AD-B1:** caught-up "today" action; how hard to demote play/shop (Figma will make this concrete).
- **AD-B3:** gate arcade or coin-economics-only (lean: economics-only).

## Notes
- B5, B6, B1 are **native-visible** → they ride native builds; batch where possible.
- Non-trivial UI (B1, parts of B6) goes **Figma-first** per the standing rule.
- Each item becomes its own SDD implementation plan (model/seam/endpoint/UI tasks) when its
  AD-decisions are locked — same loop as Theme A (per-task + opus whole-branch review).
