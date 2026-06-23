# Penny's Arcade — Design Spec

**Date:** 2026-06-23
**Status:** Approved design → ready for implementation plan
**Scope:** A games hub ("Penny's Arcade") seeded with two short-burst learning games, built on a small shared rewards/leaderboard layer so further games drop in cheaply later.

> **Out of scope (separate follow-up spec):** Avatar & Cosmetics Expansion — a dedicated avatar display surface plus three new spendable categories (Penny scene backgrounds, Penny colour/outfit skins, app/profile themes) with per-category equip slots. The Arcade feeds the **existing** 8-item Penny's Shop until that ships.

---

## 1. Goals & success criteria

**Primary goal (ranked #1): daily return / habit.** The marquee mechanic is a once-a-day puzzle surfaced on Home.

Secondary goals, in priority order: session depth/fun; concept mastery (retrieval practice); real-world value.

**Success criteria:**
- A child can open the app and play a 1–3 minute game in ≤2 taps from Home.
- A daily puzzle creates a reason to return each day, and ties into the existing streak.
- Games reinforce concepts the child has learned (retrieval practice), not teach new material.
- Rewards feed the existing coin/XP economy without inflating it (daily-capped), plus a new competitive layer.
- Fully kid-safe (no child free-text), WCAG 2.2 AA, ≥44px touch targets, works for non-readers up to teens where the game allows.

**Non-goals:** teaching new concepts inside games; real-money anything; multiplayer/real-time; the cosmetics expansion (separate spec).

---

## 2. Architecture overview

**Penny's Arcade** is a hub reachable from Home (no new bottom-tab — the nav already has 6):
- A **Home daily card** ("Today's MoneyWord") — the primary daily-return surface.
- An **Arcade hub** card/quick-link on Home → `/arcade` page listing available games.
- Per-game pages: `/arcade/quiz-rush`, `/arcade/moneyword`.

A small **shared layer** underpins all games so new ones are cheap:
- **Two reward streams from one play** (clean separation):
  - **Coins/XP (participation)** — awarded for *playing*, into the existing economy (levels + Penny's Shop). Coins == XP (1:1) in this app, so arcade play also nudges levels; therefore it is **daily-capped** via a new `arcade_xp_today` field (mirrors the existing `sim_xp_today` / `revise_xp_today` 25-XP/day caps).
  - **Arcade Points (performance)** — a **new** score earned by *how well* you play (quiz combos, fast/few-guess solves). Feeds a **weekly per-market Arcade leaderboard** (username-only, top 50 — mirrors the existing `GET /leaderboard`) and **all-time personal bests**. Not capped — it is skill-based and never buys anything.
- Both seed games are **free** (habit-first; monetisation stays with existing content/market gates).

**New backend tables** (additive migration; ask about a prod snapshot before applying):
- `arcade_score` — `id`, `user_id`, `game` (enum: `quiz_rush` | `moneyword`), `points` (int), `market_code`, `created_at`. Powers the weekly leaderboard (sum/Top-N over a rolling window) and personal bests (max).
- `arcade_word` — `id`, `word` (upper-case A–Z, 4–8 letters), `definition` (kid-safe, ≤140 chars), `language` (default `en`), `length` (derived), `status` (`pending` | `approved` | `rejected`), `source` (`llm` | `manual`), `created_at`. The MoneyWord bank.
- `arcade_daily_schedule` — `id`, `puzzle_date` (date), `language`, `word_id` (FK → `arcade_word`), unique on `(puzzle_date, language)`. The per-day word assignment; lazily filled (see §4).
- `arcade_daily_completion` — `id`, `user_id`, `game`, `puzzle_date`, `solved` (bool), `guesses` (int), `points` (int), `created_at`, unique on `(user_id, game, puzzle_date)`. Tracks "did this child do today's puzzle" for the Home card, streak credit, and idempotency.

**New columns on `UserProgress`:** `arcade_xp_today` (int, default 0), `arcade_xp_date` (date) — the daily participation-coin cap window.

**New backend modules:**
- `app/services/arcade_service.py` — scoring, XP-cap enforcement, leaderboard + personal-best queries, daily-completion recording.
- `app/services/moneyword_service.py` — daily word selection (lazy, no-repeat), guess evaluation, definition reveal.
- `app/services/arcade_word_admin_service.py` — LLM proposal + moderation of candidate words/definitions.
- `app/routers/arcade.py` — child-facing endpoints.
- `app/routers/arcade_admin.py` — admin word-bank queue (behind `get_current_admin`).

**New frontend:**
- `pages/child/Arcade.tsx` (hub), `pages/child/games/QuizRush.tsx`, `pages/child/games/MoneyWord.tsx`.
- `components/home/ArcadeDailyCard.tsx` (Home daily card) + an Arcade entry in the existing Home quick-links.
- `components/admin/ArcadeWordBank.tsx` (admin queue).
- `api/arcade.ts`, `api/arcadeAdmin.ts`.

---

## 3. Game 1 — Quiz Rush (ship first; zero new content)

**What it is:** a 60-second timed multiple-choice blitz.

**Content:** pulled from the **existing quiz lesson bank** (`Lesson.type == "quiz"`, `content_json = {question, choices, answer_index, explanation}`). The server assembles a shuffled question set, **preferring concepts the child has unlocked** (lessons they have a `LessonCompletion` for, in their `active_market_code`) for retrieval practice; if that pool is too small (cold-start threshold, e.g. <10 questions), it **falls back to all published quiz questions in their market**. No child free-text — multiple choice only.

**Loop:** answer as many as possible in 60s; a **combo multiplier** rewards consecutive correct answers; a wrong answer resets the combo (and records a weak concept via the existing `record_weak_concept`, so games feed Revise). End screen shows score, new personal best, leaderboard position, and rewards.

**Rewards:** Arcade Points = f(correct count, max combo). Coins/XP awarded for participation, subject to the daily `arcade_xp_today` cap. Replayable endlessly for Points; coins stop accruing once the daily cap is hit (UI shows "you've earned today's coins — keep playing for points!").

**Endpoints:**
- `GET /arcade/quiz-rush/session` → a server-built question set **including answer keys**, so the client can give instant per-question feedback (essential to a 60s blitz). This is an accepted trade-off: the only thing at stake is a cosmetic leaderboard, so heavy anti-cheat (per-answer round-trips) is not worth the latency. See §7.
- `POST /arcade/quiz-rush/score` → `{answers: [{question_id, choice_index, time_ms}]}` → the server **re-scores authoritatively from the submitted choices** (the client-side feedback is convenience only and never sets the official score), records `arcade_score`, applies capped coins/XP, returns `{points, coins_awarded, personal_best, leaderboard_rank}`.

---

## 4. Game 2 — MoneyWord (the daily anchor; serves goal #1)

**What it is:** a daily Wordle-style finance-term puzzle.

**Mechanic:** guess the term in **6 tries**; each guess returns per-letter feedback — `correct` (right letter, right spot), `present` (right letter, wrong spot), `absent`. Word length is **variable 4–8 letters** and shown up-front, so real finance vocab fits (debt, asset, budget, interest). **On finish (win or loss) the kid-friendly definition is revealed — the learning moment.** A shareable emoji-grid result encourages social spread.

**Daily, same-for-everyone:** one word **per language per UTC day** (UTC chosen for consistency with the app's existing daily mechanics). Same word for everyone sharing a language → comparable scores + shareable. **Launch English-only** (live markets are EN); `arcade_word.language` carries the axis for future languages.

**Word selection — lazy, no-repeat, no cron:** on the first request for a given `(date, language)`, the server selects the **least-recently-scheduled approved word** (an approved word never previously in `arcade_daily_schedule`, else the oldest-scheduled), inserts a unique `(puzzle_date, language)` row, and serves it. The unique constraint makes concurrent first-requests idempotent. No cron job and no `DailyPuzzle` precompute needed.

**Once per day:** a child plays today's word once. `arcade_daily_completion` enforces idempotency and drives the Home card state (Play → In progress → Done ✓) and streak credit.

**Rewards:** Arcade Points scale inversely with guesses used (fewer guesses = more points); solving credits the daily streak and capped participation coins/XP. On completion the server writes **both** an `arcade_score` row (`game="moneyword"` — so MoneyWord shares the unified weekly leaderboard + personal bests) and the `arcade_daily_completion` row (once-a-day idempotency + Home-card state + streak credit).

**Endpoints:**
- `GET /arcade/moneyword/today` → `{length, guesses_used, state, already_solved}` (no answer in payload).
- `POST /arcade/moneyword/guess` → `{guess}` → server validates length + dictionary membership, returns per-letter feedback, decrements remaining guesses, and on completion returns `{solved, definition, points, coins_awarded, share_grid}`. Server-authoritative; the word is never sent to the client until the puzzle ends.

---

## 5. Admin — MoneyWord word bank

A small admin queue mirroring the existing video-curation / market-content tooling:
- `POST /admin/arcade-words/suggest` → LLM proposes N finance words + kid-safe definitions for a target language; output passes `moderate_output`; rows inserted as `status="pending"`. (Uses the existing LLM + moderation conventions; rate-limited like other LLM endpoints.)
- `GET /admin/arcade-words?status=` → review queue.
- `POST /admin/arcade-words/{id}/approve` (with optional edits to word/definition) and `/reject`.
- Only `status="approved"` words ever enter rotation.
- Validation: word is 4–8 letters, A–Z only, unique per language; definition non-empty, ≤140 chars, no proper nouns/answer leakage.

This keeps the bank growable to 300+ words cheaply while the operator stays in control of every word a child sees.

---

## 6. Data flow (happy paths)

- **Daily return:** open app → Home shows `ArcadeDailyCard` (state from `arcade_daily_completion`) → tap → MoneyWord → guesses scored server-side → finish reveals definition + Points + streak credit + share grid → card flips to Done ✓.
- **Anytime play:** Home → Arcade hub → Quiz Rush → 60s blitz → server scores → personal best + leaderboard + capped coins.
- **Leaderboard:** `GET /arcade/leaderboard?game=` → weekly per-market Top-50 by summed Points (username + country only).
- **Operator:** admin generates word candidates → moderates/approves → words enter the lazy daily rotation.

---

## 7. Safety, a11y, i18n

- **Child safety:** no child free-text anywhere — MoneyWord input is letter tiles (A–Z keyboard), Quiz Rush is multiple choice. All definitions are LLM-moderated **and** human-approved before any child sees them. Scoring is **server-authoritative** in both games. The MoneyWord answer word is **never sent to the client until the puzzle ends** (the whole game is guessing it). Quiz Rush ships answer keys for instant feedback but the server re-scores from submissions (see §3) — acceptable because nothing of real-world value is at stake.
- **A11y (WCAG 2.2 AA):** letter feedback is **never colour-only** — pair colour with icons/patterns and text labels (e.g. ✓ / ↔ / ✕ + `aria-label`); ≥44px touch targets; full keyboard play; screen-reader announcements for guess results and timer; reduced-motion respected. New UI gets `vitest-axe` coverage.
- **i18n:** all UI strings localised via the existing i18n setup. The MoneyWord word bank is language-scoped; launch ships `en` only.

---

## 8. Testing

**Backend (pytest, async session-scoped fixtures):**
- Quiz Rush authoritative scoring (correct/combo math); withheld answers in the session payload.
- `arcade_xp_today` cap: coins stop at the daily cap; Points continue; cap resets next local/UTC day.
- MoneyWord guess evaluation: correct/present/absent including duplicate letters; length + dictionary validation; win/lose definition reveal.
- Daily selection: lazy insert, **no-repeat** ordering, idempotent under concurrent first-request (unique constraint).
- `arcade_daily_completion` idempotency (one play/day) + streak credit.
- Leaderboard + personal-best queries (per-market, windowed, Top-N).
- Admin word bank: suggest → moderation gate → approve/reject; only approved words rotate; validation rejects bad words.

**Frontend (vitest + vitest-axe):**
- Hub renders available games; Home daily card reflects Play / In-progress / Done states.
- Quiz Rush timer/combo/score flow; MoneyWord tile grid + keyboard + feedback rendering; share grid.
- Axe checks on hub, both games, admin queue.

CI: backend `ruff` + pytest; frontend `tsc` + lint + vitest + build. iOS-visible (new child screens) → `npm run build && npx cap sync ios` before any device build.

---

## 9. Build phasing (one spec, two shippable phases)

- **Phase 1 — Arcade foundation + Quiz Rush:** shared `arcade_score` + `arcade_xp_today` + leaderboard infra, the hub page + Home Arcade entry, and Quiz Rush end-to-end (zero new content). Ships a complete, playable arcade fast.
- **Phase 2 — MoneyWord + word bank + daily infra:** `arcade_word` + `arcade_daily_schedule` + `arcade_daily_completion`, the admin word-bank queue, lazy daily selection, the MoneyWord game, and the Home daily card. Delivers the #1 daily-return mechanic.

Each phase is independently testable and shippable.

---

## 10. Decisions captured (resolved during brainstorm)

- Seed games: **Quiz Rush + MoneyWord**.
- Placement: **Home daily card + Arcade hub via Home**, no new bottom tab.
- Rewards: **capped coins/XP for playing + uncapped Arcade Points for skill** (new weekly per-market leaderboard + personal bests).
- Gating: **both games free**.
- MoneyWord word bank: **LLM-assisted + admin-approved**; launch **English-only**; variable length 4–8.
- Daily word: **deterministic lazy no-repeat selection, no cron**.
- Quiz Rush content: **prefer the child's unlocked concepts, fall back to all-market**.
- Coin sink: Arcade feeds the **existing** 8-item shop now; the richer sink (avatar surface + 3 new cosmetic categories) is a **separate follow-up spec**.
