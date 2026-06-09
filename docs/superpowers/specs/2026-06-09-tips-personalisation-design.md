# Personalised Investing Tips (Items 3.2 + 3.3) — Design Spec

**Date:** 2026-06-09
**Status:** Approved (design) — pending implementation plan
**Repo:** `ashmorel/investikid` · branch `testing`
**Backlog ref:** Simulator/Market improvements **Item 3.2** (personalise tips to holdings/level) + **Item 3.3** (per-child freshness), building on shipped **3.1** (tip rotation). `docs/superpowers/specs/2026-06-08-simulator-market-improvements-backlog.md`.
**Scope:** Backend LLM personalisation of `GET /market/tips` + frontend "New tips" + "For you" badge. **No DB migration** (cache only). It's a kids' app — moderated fail-closed, rate-limited, WCAG 2.2 AA.

## Goal
Make Investing Tips *feel personal*: keep the generic educational tips, and add **2** tips tailored to the child's **holdings + learning stage** ("Since you own Apple…"), with a **"New tips"** refresh. Free for all users; no premium gate.

## Current state (verified)
`GET /market/tips` → `_generate_tips()` (`app/routers/simulator.py:583-622`): single **global** cache key `"global"` (`_TIPS_CACHE_TTL = 3600`), 6 LLM tips (tier "lite", temp 0.9, `_TIPS_PROMPT`), `_FALLBACK_TIPS` (3 static). **No DB session, no user context, no rate limit**; moderation is best-effort (`moderate_output(surface="tips")`) with **no AuditLog** (no session in scope). The richer template is `GET /market/news-summary` (`:171-243`): `@limiter.limit("20/hour")` + `session` + holdings fetch + age from `dob` + `moderate_output` that writes `AuditLog(event_type="moderation_block", metadata_json={"surface":…, "category":…})` on unsafe. `InvestingTipOut` lives in `app/schemas/simulator.py`; the FE `InvestingTips.tsx` already accepts `contextTicker`/`contextExchange` and (since 3.1) auto-rotates with play/pause inside a collapsible `SectionCard`.

---

## Section 1 — Schema (additive, no migration)
`InvestingTipOut` (`app/schemas/simulator.py`) gains an optional field:
- `personalised: bool = False` — flags a holdings/level-tailored tip so the FE can badge it "For you". Backwards-compatible (default false; existing generic tips and `_FALLBACK_TIPS` are all false).

FE mirror: `InvestingTip` type in `frontend/src/api/simulator.ts` gains `personalised?: boolean`.

## Section 2 — Context gathering (backend)
Evolve `get_investing_tips` to take `request: Request`, `current_user`, `session`, decorate `@limiter.limit("30/hour")`, and accept `refresh: bool = False` query param. Gather:
- **Holdings:** `Portfolio` → `Holding` (ticker, exchange, name) for `current_user` — same query as news-summary. Cap to a handful (e.g. first 5) for the prompt.
- **Learning stage:** a cheap bucket from the completed-lesson count — `select(func.count(LessonCompletion.id)).where(LessonCompletion.user_id == current_user.id)` (the pattern at `recommendation_service.py:429-430`). Bucket: `0 → "new"`, `1–5 → "beginner"`, `6–15 → "intermediate"`, `16+ → "advanced"`. (Coarse on purpose — no heavy `derive_level_states`.)
- **Age:** `(date.today() - current_user.dob).days // 365` (as news-summary).

## Section 3 — Hybrid generation
A new service function `generate_personalised_tips(holdings, stage, age) -> list[InvestingTipOut]` (extract tip logic into `app/services/tips_service.py`, moving `_TIPS_PROMPT`/`_FALLBACK_TIPS`/the generic generator there too so the router thins out):
- **Generic base:** unchanged `_TIPS_PROMPT` generator, **global** 1h cache (cost control). All `personalised=False`.
- **Personalised slice (2 tips):** one LLM call (tier "lite") with a prompt that gets the child's age, stage bucket, and up to 5 holdings (ticker + name); asks for exactly 2 short, encouraging, age-appropriate tips that reference an owned stock and/or the concept the child is learning, **never giving real investment advice**, same JSON shape, `example_ticker` chosen from the child's holdings where natural. Mark these `personalised=True`.
- **Compose:** personalised first, then generic; dedupe by `id`/title; **cap at 6** total. If the child has **no holdings AND stage == "new"** → skip the personalised call entirely and return generic only (graceful; matches today).

## Section 4 — Safety (kids' app)
- **Moderation:** moderate the personalised tips' combined text via `moderate_output(surface="tips")`. On `not safe`: **fail closed** — drop the personalised slice (return generic only) AND, since `session`+`current_user` are now in scope, write `AuditLog(user_id=current_user.id, event_type="moderation_block", metadata_json={"surface":"tips","category":_mod.category})` + commit (mirrors news-summary). Generic base keeps its own existing moderation.
- **Rate limit:** `@limiter.limit("30/hour")` (tips are lighter than news-summary's 20/hour but still LLM-backed).
- **Failure isolation:** any LLM/JSON error in the personalised slice is swallowed → generic only (never 500, never blocks the page). Reuse `_FALLBACK_TIPS` if even the generic generator fails (current behaviour).
- **No PII** beyond age + owned tickers + stage label in the prompt. **Free** — no premium gate. No DB writes except the AuditLog-on-block.

## Section 5 — Freshness / caching (3.3)
- **Per-child cache** for the *personalised slice* keyed on `(user_id, holdings_signature, stage, age)` where `holdings_signature` = sorted tickers joined (so it auto-invalidates when holdings change), TTL 1h. Generic base keeps the global cache.
- **`?refresh=true`** bypasses the per-child cache for that request (still rate-limited), regenerates the personalised slice, and re-stores it. Generic base is unaffected by refresh (stays globally cached).

## Section 6 — Frontend
- `simulatorApi.getInvestingTips(refresh?: boolean)` → `apiFetch('/market/tips' + (refresh ? '?refresh=true' : ''))`.
- `InvestingTips.tsx`: add a **"New tips"** button in the card-body toolbar (next to play/pause) — lucide `Sparkles` (or `RefreshCw`), `aria-label="Get new tips"`, disabled + spinner while refetching (respect `prefers-reduced-motion` — no spin animation under reduced motion), invalidates/refetches the `['investing-tips']` query with `refresh`. Tapping resets rotation to the first tip.
- **"For you" badge:** tips with `personalised` render a small brand chip ("For you") in the tip card. Decorative text, sufficient contrast.
- Preserve all 3.1 rotation/a11y behaviour and the collapsible SectionCard.

## Testing
**Backend (pytest, authed client + `app.dependency_overrides`/monkeypatch the LLM + `moderate_output`):**
- Personalised tips generated when holdings+stage present; `personalised=True` on exactly the tailored ones; total ≤6.
- No holdings AND stage "new" → generic only (no personalised call); response still valid.
- Moderation unsafe → personalised slice dropped, generic returned, **AuditLog moderation_block written** (surface "tips").
- Per-child cache hit (second call, same context, no LLM re-call); `?refresh=true` bypasses it.
- Stage bucketing thresholds (0/new, boundary cases).
- LLM error in personalised slice → generic only, no 500.
- `?refresh=zzz`/invalid bool handled (FastAPI bool coercion) and rate-limit decorator present.

**Frontend (vitest + vitest-axe):**
- `getInvestingTips(true)` hits `?refresh=true`; button click triggers a refetch with refresh.
- `personalised` tips show the "For you" badge; generic ones don't.
- "New tips" button is labelled, disabled while loading, axe-clean; reduced-motion suppresses spin.
- Existing rotation/pause/dots/reduced-motion tests still pass.

## Verification
Backend: `/Users/leeashmore/Local Repo/.venv/bin/ruff check . && /Users/leeashmore/Local Repo/.venv/bin/pytest`. Frontend: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`. No `cap sync`. Work on `testing`; do not promote.

## Out of scope
Changing the generic tip content; premium gating; persisting tips to the DB (cache only); `derive_level_states`-based fine-grained level targeting; the Coach; any DB migration.
