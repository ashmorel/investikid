# AI-Authored Level 2/3 Pilot — "What is a Stock?" — Design Spec

**Date:** 2026-06-09
**Status:** Approved (curriculum + workflow) — **content below awaiting your in-repo review** → then implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Programme:** Part **#3** of the leveling programme. Depends on **#2** (leveling + premium model, shipped — `is_premium = order_index >= 2`). Pilots **one module** before any rollout.

## Goal
Add a free **Level 2** and a premium **Level 3** to the "What is a Stock?" module as **version-controlled seed content** (AI-drafted to an agreed curriculum, reviewed by you here, then committed to `seed/content.py`), validating the multi-level + premium experience end-to-end on a real module.

## Decisions (from brainstorming)
- **Authoring:** seed-authored, AI-drafted, reviewed in-repo (this doc) → committed to seed. (Not the live admin pipeline — keeps content version-controlled + promotable testing→staging→prod.)
- **Curriculum ladder** (revised after finding L1 already covers dividends/price-moves/%):
  - **L1 (exists, free):** what a stock is, ownership, dividends, why prices move, % gains, don't panic-sell.
  - **L2 (free) — "How the stock market works":** exchanges, tickers, trading with other investors, indices as scoreboards, market cap, + Simulator practice tie-in.
  - **L3 (premium) — "Investing wisely for the long run":** diversification, time-in-market, funds/index, risk vs reward.
- **Naming:** generic "Level 2" / "Level 3" (per #2).
- **Premium:** automatic — Level 3 is `order_index 2` → premium via the #2 rule. No flag to set.

## Content schemas (match existing lessons exactly)
- `card`: `{title, body}`
- `quiz`: `{question, choices: [str,...], answer_index: int, explanation}`
- `scenario`: `{prompt, choices: [{label, outcome}], correct_index: int}`
- xp: cards 10, quizzes 25, scenarios 20 (matches L1). **No `video` lessons** (avoid inventing YouTube IDs that the video-health cron would flag dead).

---

## Level 2 — "How the stock market works" (free, order_index 1) — REVIEW THIS

1. **card** — *"Where stocks are bought and sold"*
   > Stocks are traded on a **stock exchange** — a giant marketplace like the London Stock Exchange (LSE) or the New York Stock Exchange. Here's the surprise: when you buy a share, you're usually **not** buying it from the company. You're buying it from another investor who wants to sell theirs.
2. **card** — *"Every stock has a ticker"*
   > A **ticker** is a short code that names a stock — like **AAPL** for Apple or **TSLA** for Tesla. Tickers make companies quick to find. Try searching one in the practice **Simulator** to see its price!
3. **quiz** — "When you buy a share of a big company like Apple, who are you usually buying it from?"
   - The company itself, directly
   - **Another investor who wants to sell their share** ✓
   - The government
   - Your bank's savings team
   - *explanation:* Most of the time you trade with other investors on an exchange — not the company. The company only sold those shares once, long ago.
4. **quiz** — "What is a stock exchange?"
   - **A marketplace where shares are bought and sold** ✓
   - A shop that only sells company products
   - A savings account for grown-ups
   - A type of dividend
   - *explanation:* An exchange (like the LSE or NYSE) is the marketplace where buyers and sellers trade shares.
5. **quiz** — "You hear about the 'FTSE 100' or 'S&P 500'. What is an index like that?"
   - A single company's share price
   - **A scoreboard that tracks many big companies at once** ✓
   - A tax on investors
   - A list of dividends
   - *explanation:* An index is like a scoreboard: it follows lots of companies together, so people can see how 'the market' is doing overall.
6. **quiz** — "Company A is worth £1 trillion. Company B is worth £10 million. Which is the 'bigger' company by market value?"
   - **Company A** ✓
   - Company B
   - They're exactly the same
   - You can't tell from value
   - *explanation:* A company's total value is its 'market cap'. £1 trillion is far bigger than £10 million — Company A is the giant.
7. **scenario** — "You're curious how a real company's share price moves, but you're brand new. What's the smartest first step?"
   - "Put your real birthday money straight into one stock" → *Risky — never invest real money you can't afford to lose, especially before you've learned the ropes.*
   - **"Search its ticker in the practice Simulator and watch it with pretend money"** ✓ → *Perfect — the Simulator lets you explore real prices and practise with zero risk before any real money is involved.*
   - "Buy whatever a video online tells you to" → *Be careful — lots of online 'tips' are hype or scams. Learn and practise first, and always ask a trusted grown-up.*

## Level 3 — "Investing wisely for the long run" (premium, order_index 2) — REVIEW THIS

1. **card** — *"Don't put all your eggs in one basket"*
   > If you put all your money into one company and it does badly, you could lose a lot. Spreading your money across many different companies is called **diversification** — if one struggles, the others can balance it out.
2. **card** — *"Time in the market beats timing the market"*
   > Nobody — not even experts — can reliably guess the best day to buy or sell. Investors who **stay invested for many years** usually do better than those who jump in and out trying to be clever.
3. **quiz** — "Which is generally LESS risky?"
   - Putting all your money in one company
   - **Spreading your money across many different companies** ✓
   - They're equally risky
   - Keeping it all as cash under your bed
   - *explanation:* Spreading out (diversifying) means one bad company won't sink everything. That's a core rule of smart investing.
4. **quiz** — "What is an index fund?"
   - A single risky company
   - **A basket that holds many companies at once, giving instant diversification** ✓
   - A loan you take out to invest
   - A type of bank fee
   - *explanation:* An index fund holds lots of companies together — buying one is like buying a whole scoreboard of businesses at once.
5. **quiz** — "Trying to guess the perfect day to buy or sell is called 'timing the market'. Is it a reliable way to invest?"
   - Yes, anyone can do it easily
   - **No — even experts can't do it reliably, so staying invested long-term usually works better** ✓
   - Yes, if you watch the news every hour
   - Only on weekends
   - *explanation:* Short-term prices are unpredictable. Patience and time usually beat trying to guess the perfect moment.
6. **quiz** — "Investments that could grow a lot usually also carry…"
   - **More risk of falling in value** ✓
   - A guarantee from the government
   - No risk at all
   - Free money
   - *explanation:* Higher possible reward almost always comes with higher risk. There's no reward with zero risk — that's the trade-off.
7. **scenario** — "You have £100 of pretend money to invest for 10 years in the Simulator. What's the wisest approach?"
   - "Put all £100 into the one stock a friend is hyping" → *Too risky — if that single company struggles, your whole £100 is exposed. No diversification.*
   - **"Spread it across several companies (or a fund) and leave it to grow"** ✓ → *Wise — diversifying and giving it years to grow is exactly how patient investors lower risk and let compounding work.*
   - "Buy and sell every single day to chase quick wins" → *This is 'timing the market' — unreliable, stressful, and usually loses to just staying invested.*

---

## Seeding approach (implementation)
The seed (`seed_modules_and_lessons`) currently creates **one Level 1** per module from `spec["lessons"]`. Extend it to support optional extra levels **without changing behaviour for other modules**:
- Add an optional `"extra_levels"` key to a module spec: a list of `{"title": str, "lessons": [...]}`. The "What is a Stock?" module gets two entries (Level 2, Level 3 above).
- In `seed_modules_and_lessons`, after the Level-1 block: for each extra level at position `i` (starting at **1**), find-or-create the `Level` (matched by `module_id` + `order_index == i`), with `title=<given>`, `order_index=i`, `is_premium=premium_for_position(i)`, `pass_threshold=0.7`, `content_source="authored"`, then insert its lessons with the **same idempotent identity-based** logic used for Level 1 (extract that lesson-insertion block into a helper `_ensure_level_lessons(session, module, level, lesson_specs)` and call it for Level 1 and each extra level).
- Idempotent: re-seeding doesn't duplicate levels or lessons; existing admin reordering survives (same merge logic).
- **No migration** (seed-only data; runs on every deploy). Generic single-level modules are unaffected (no `extra_levels` key → unchanged).

## Testing
**Backend (pytest, `db_session`):**
- After seeding (in the seeded-DB fixture), "What is a Stock?" has **3 levels** at order_index 0/1/2; Level 1–2 `is_premium False`, Level 3 `is_premium True`; lesson counts per level = 8 / 6 / 7 (or assert ≥ expected, robust to L1 edits).
- Re-running the seed is idempotent (level + lesson counts unchanged).
- Content sanity (unit, no DB): every drafted quiz has `0 <= answer_index < len(choices)`; every scenario has `0 <= correct_index < len(choices)` and each choice has `label` + `outcome`; every card has non-empty `title` + `body`. (A small data-driven test over the `extra_levels` specs.)
- End-to-end gate (reuse #2's pattern): a non-premium child sees Level 3 `locked_reason="premium"`; a premium child does not.

## Verification
Backend: `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest`. No migration, no FE change, no `cap sync`. Work on `testing`; do NOT promote. (When promoted, the new levels appear after each env's seed runs on deploy — no snapshot concern since it's additive seed data, but the #2 data migration in the same batch still triggers the standing snapshot ask.)

## Out of scope
Rolling Level 2/3 out to other modules (this is the one-module pilot); the live admin AI generate-UI path (unused here); premium-discoverability surfaces (**#4**); any change to L1 content or the progression/pass-threshold rules.
